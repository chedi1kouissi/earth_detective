"""Thin wrapper around Gemini (google-genai): JSON answers, text answers and a tool-calling loop.

Models: GEMINI_MODEL in .env (reasoning) and GEMINI_FAST_MODEL (quick steps). If a model is not
available, the next one in the fallback list is tried.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable

from common import config as C

log = logging.getLogger(__name__)

PRO_MODELS = [m for m in (C.GEMINI_MODEL, "gemini-pro-latest", "gemini-2.5-pro") if m]
FAST_MODELS = [m for m in (os.getenv("GEMINI_FAST_MODEL", "").strip(), "gemini-flash-latest",
                           "gemini-2.5-flash") if m]


class LLMUnavailable(RuntimeError):
    pass


_client = None


def client():
    global _client
    if _client is None:
        if not C.GEMINI_API_KEY:
            raise LLMUnavailable("GEMINI_API_KEY is missing in .env")
        from google import genai
        os.environ.pop("GOOGLE_API_KEY", None)  # avoid the 'both keys set' ambiguity
        _client = genai.Client(api_key=C.GEMINI_API_KEY)
    return _client


def _call(models: list[str], fn: Callable[[str], Any], retries: int = 3):
    """Try each model; retry transient errors (429 / 5xx) with backoff."""
    last = None
    for model in models:
        for attempt in range(retries):
            try:
                return model, fn(model)
            except Exception as e:  # noqa: BLE001 - SDK raises several error classes
                msg = str(e)
                last = e
                if "404" in msg or "not found" in msg.lower() or "not supported" in msg.lower():
                    log.warning("model %s unavailable, trying the next one", model)
                    break
                if any(code in msg for code in ("429", "500", "502", "503", "504", "UNAVAILABLE",
                                                "RESOURCE_EXHAUSTED", "overloaded")):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
    raise LLMUnavailable(f"Gemini call failed: {last}")


def generate_text(prompt: str, system: str = "", fast: bool = False,
                  temperature: float = 0.3) -> str:
    from google.genai import types
    cfg = types.GenerateContentConfig(system_instruction=system or None, temperature=temperature)
    _, r = _call(FAST_MODELS if fast else PRO_MODELS,
                 lambda m: client().models.generate_content(model=m, contents=prompt, config=cfg))
    return (r.text or "").strip()


def generate_json(prompt: str, schema: dict, system: str = "", fast: bool = True,
                  temperature: float = 0.1) -> dict:
    from google.genai import types
    cfg = types.GenerateContentConfig(system_instruction=system or None, temperature=temperature,
                                      response_mime_type="application/json",
                                      response_json_schema=schema)
    _, r = _call(FAST_MODELS if fast else PRO_MODELS,
                 lambda m: client().models.generate_content(model=m, contents=prompt, config=cfg))
    try:
        return json.loads(r.text)
    except (TypeError, ValueError) as e:
        raise LLMUnavailable(f"Gemini did not return valid JSON: {r.text!r}") from e


def run_tools(system: str, user_message: str, tool_schemas: dict[str, dict],
              call_tool: Callable[[str, dict], dict], max_turns: int = 60,
              on_event: Callable[[dict], None] | None = None, fast: bool = False,
              stop_tool: str | None = None) -> str:
    """Generic tool-calling loop. Returns the model's final text."""
    from google.genai import types
    decls = [types.FunctionDeclaration(
        name=name, description=(s.get("description") or "").strip(),
        parameters_json_schema={"type": "object", "properties": s.get("properties", {}),
                                "required": s.get("required", [])})
        for name, s in tool_schemas.items()]
    cfg = types.GenerateContentConfig(
        system_instruction=system, temperature=0.2,
        tools=[types.Tool(function_declarations=decls)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents: list = [types.Content(role="user", parts=[types.Part(text=user_message)])]
    models = FAST_MODELS if fast else PRO_MODELS
    emit = on_event or (lambda e: None)
    for turn in range(max_turns):
        model, r = _call(models, lambda m: client().models.generate_content(
            model=m, contents=contents, config=cfg))
        models = [model]                          # stick to the model that worked
        cand = r.candidates[0] if r.candidates else None
        if cand is None or cand.content is None:
            emit({"type": "empty", "turn": turn})
            break
        contents.append(cand.content)             # keeps thought signatures for the next turn
        calls = [p.function_call for p in cand.content.parts or [] if p.function_call]
        text = "".join(p.text or "" for p in cand.content.parts or [] if p.text and not
                       getattr(p, "thought", False))
        if text.strip():
            emit({"type": "text", "turn": turn, "text": text.strip()})
        if not calls:
            return text.strip()
        responses = []
        stop = False
        for fc in calls:
            args = dict(fc.args or {})
            result = call_tool(fc.name, args)
            emit({"type": "tool", "turn": turn, "name": fc.name, "args": args, "result": result})
            responses.append(types.Part.from_function_response(name=fc.name,
                                                                response={"result": result}))
            stop = stop or (stop_tool is not None and fc.name == stop_tool)
        contents.append(types.Content(role="user", parts=responses))
        if stop:
            return "stopped by " + stop_tool
    return "max turns reached"
