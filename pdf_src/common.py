"""Shared styles, layout helpers and diagram primitives for the EarthSleuth PDFs."""
import math
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether,
                                ListFlowable, ListItem, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------- fonts
FD = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Body", os.path.join(FD, "arial.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", os.path.join(FD, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Body-Italic", os.path.join(FD, "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Body-BoldItalic", os.path.join(FD, "arialbi.ttf")))
pdfmetrics.registerFont(TTFont("Mono", os.path.join(FD, "consola.ttf")))
addMapping("Body", 0, 0, "Body")
addMapping("Body", 0, 1, "Body-Italic")
addMapping("Body", 1, 0, "Body-Bold")
addMapping("Body", 1, 1, "Body-BoldItalic")

# ---------------------------------------------------------------- colours
NAVY = colors.HexColor("#0B2545")
BLUE = colors.HexColor("#1F5FA8")
SKY = colors.HexColor("#EAF2FB")
TEAL = colors.HexColor("#138A7E")
TEAL_L = colors.HexColor("#E3F4F1")
ORANGE = colors.HexColor("#E58A2B")
CREAM = colors.HexColor("#FFF5E1")
RED = colors.HexColor("#C8423B")
ROSE = colors.HexColor("#FBE9E7")
PURPLE = colors.HexColor("#6A4FA0")
LILAC = colors.HexColor("#F0EBF8")
GREY = colors.HexColor("#5B6573")
LGREY = colors.HexColor("#F3F5F8")
MGREY = colors.HexColor("#C9D1DB")
INK = colors.HexColor("#1D2430")

PAGE_W, PAGE_H = A4
MARGIN = 52
CONTENT_W = PAGE_W - 2 * MARGIN

# ---------------------------------------------------------------- styles
S = {}
S["body"] = ParagraphStyle("body", fontName="Body", fontSize=10, leading=14.2,
                           textColor=INK, spaceAfter=6)
S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=8.5, leading=11.5,
                            textColor=GREY)
S["cell"] = ParagraphStyle("cell", parent=S["body"], fontSize=8.6, leading=11.4,
                           spaceAfter=0)
S["cellh"] = ParagraphStyle("cellh", parent=S["cell"], fontName="Body-Bold",
                            textColor=colors.white)
S["H1"] = ParagraphStyle("H1", fontName="Body-Bold", fontSize=19, leading=24,
                         textColor=NAVY, spaceBefore=4, spaceAfter=10)
S["H1x"] = ParagraphStyle("H1x", parent=S["H1"])
S["H2"] = ParagraphStyle("H2", fontName="Body-Bold", fontSize=13.5, leading=18,
                         textColor=BLUE, spaceBefore=12, spaceAfter=6)
S["H3"] = ParagraphStyle("H3", fontName="Body-Bold", fontSize=11, leading=15,
                         textColor=NAVY, spaceBefore=8, spaceAfter=4)
for _k in ("H1", "H2", "H3"):
    S[_k].keepWithNext = 1
S["boxtitle"] =ParagraphStyle("boxtitle", fontName="Body-Bold", fontSize=9.5,
                               leading=13, spaceAfter=3)
S["boxbody"] = ParagraphStyle("boxbody", parent=S["body"], fontSize=9.4,
                              leading=13.2, spaceAfter=3)
S["diag"] = ParagraphStyle("diag", fontName="Body", fontSize=8, leading=10,
                           alignment=TA_CENTER, textColor=INK)
S["toc1"] = ParagraphStyle("toc1", fontName="Body-Bold", fontSize=10.5,
                           leading=16, leftIndent=0, textColor=NAVY)
S["toc2"] = ParagraphStyle("toc2", fontName="Body", fontSize=9.3, leading=13,
                           leftIndent=18, textColor=INK)
S["code"] = ParagraphStyle("code", fontName="Mono", fontSize=7.6, leading=9.8,
                           textColor=INK)


def P(text, style="body"):
    return Paragraph(text, S[style] if isinstance(style, str) else style)


def H1(text):
    return P(text, "H1")


def H2(text):
    return P(text, "H2")


def H3(text):
    return P(text, "H3")


def SP(h=6):
    return Spacer(1, h)


def bullets(items, style="body", numbered=False, indent=14):
    st = S[style]
    flow = []
    for it in items:
        if isinstance(it, (list, tuple)):
            head, sub = it
            inner = [Paragraph(head, st), bullets(sub, style, indent=12)]
            flow.append(ListItem(inner, leftIndent=indent))
        else:
            flow.append(ListItem(Paragraph(it, st), leftIndent=indent))
    kw = dict(bulletType="1" if numbered else "bullet", leftIndent=indent,
              bulletFontName="Body-Bold" if numbered else "Body",
              bulletFontSize=9 if numbered else 8, bulletColor=BLUE)
    if not numbered:
        kw["start"] = "\u2022"
    return ListFlowable(flow, **kw)


BOX_KINDS = {
    "kid": ("Explain it like I'm 10", CREAM, ORANGE),
    "rule": ("Golden rule", ROSE, RED),
    "example": ("Example", TEAL_L, TEAL),
    "note": ("Good to know", SKY, BLUE),
    "owner": ("Who owns this", LILAC, PURPLE),
    "warn": ("Watch out", ROSE, RED),
    "future": ("Future work", LILAC, PURPLE),
}


def box(kind, content, title=None):
    t, bg, border = BOX_KINDS[kind]
    title = title or t
    ts = ParagraphStyle("bt", parent=S["boxtitle"], textColor=border)
    inner = [Paragraph(title, ts)]
    if isinstance(content, str):
        content = [content]
    for c in content:
        inner.append(Paragraph(c, S["boxbody"]) if isinstance(c, str) else c)
    tb = Table([[inner]], colWidths=[CONTENT_W])
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([SP(3), tb, SP(7)])


def table(rows, widths, header=True, font=None, head_bg=NAVY, zebra=True,
          align_top=True):
    cs = S["cell"] if font is None else ParagraphStyle("c2", parent=S["cell"],
                                                       fontSize=font, leading=font * 1.32)
    hs = ParagraphStyle("h2", parent=cs, fontName="Body-Bold", textColor=colors.white)
    total = sum(widths)
    widths = [w * CONTENT_W / total for w in widths]
    data = []
    for i, r in enumerate(rows):
        st = hs if (header and i == 0) else cs
        data.append([Paragraph(c, st) if isinstance(c, str) else c for c in r])
    tb = Table(data, colWidths=widths, repeatRows=1 if header else 0, spaceAfter=9)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, MGREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP" if align_top else "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), head_bg))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if (i % 2 == 0) == header:
                style.append(("BACKGROUND", (0, i), (-1, i), LGREY))
    tb.setStyle(TableStyle(style))
    return KeepTogether([tb]) if len(rows) <= 9 else tb


def code(text, title=None):
    pre = Preformatted(text.strip("\n"), S["code"])
    inner = [pre] if not title else [P(title, ParagraphStyle(
        "ct", parent=S["small"], fontName="Body-Bold", textColor=GREY)), pre]
    tb = Table([[inner]], colWidths=[CONTENT_W])
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LGREY),
        ("BOX", (0, 0), (-1, -1), 0.5, MGREY),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return KeepTogether([SP(2), tb, SP(8)])


def caption(text):
    return P("<i>" + text + "</i>", ParagraphStyle(
        "cap", parent=S["small"], alignment=TA_CENTER, spaceBefore=3, spaceAfter=10))


# ---------------------------------------------------------------- diagrams
class Diagram(Flowable):
    """Boxes + arrows drawn in a fixed-size canvas area (points, origin bottom-left).

    boxes:  {id: dict(x, y, w, h, text, fill, stroke, tc, fs, bold)}
    arrows: [dict(pts=[(id, side) | (x, y), ...], label, color, dashed, both)]
    groups: [dict(x, y, w, h, title, fill, stroke)]
    texts:  [dict(x, y, text, fs, color, bold, anchor)]
    """

    def __init__(self, width, height, boxes, arrows=(), groups=(), texts=()):
        super().__init__()
        self.width, self.height = width, height
        self.boxes, self.arrows, self.groups, self.texts = boxes, arrows, groups, texts

    def wrap(self, aw, ah):
        return self.width, self.height

    def _anchor(self, ref):
        if isinstance(ref[0], str):
            b = self.boxes[ref[0]]
            side = ref[1]
            f = ref[2] if len(ref) > 2 else 0.5
            x, y, w, h = b["x"], b["y"], b["w"], b["h"]
            return {"top": (x + w * f, y + h), "bottom": (x + w * f, y),
                    "left": (x, y + h * f), "right": (x + w, y + h * f),
                    "center": (x + w / 2, y + h / 2)}[side]
        return ref

    @staticmethod
    def _head(c, x1, y1, x2, y2, col, size=5.5):
        ang = math.atan2(y2 - y1, x2 - x1)
        p = c.beginPath()
        p.moveTo(x2, y2)
        p.lineTo(x2 - size * math.cos(ang - 0.42), y2 - size * math.sin(ang - 0.42))
        p.lineTo(x2 - size * math.cos(ang + 0.42), y2 - size * math.sin(ang + 0.42))
        p.close()
        c.setFillColor(col)
        c.drawPath(p, stroke=0, fill=1)

    def draw(self):
        c = self.canv
        # center the drawing horizontally in the frame
        for g in self.groups:
            c.setFillColor(g.get("fill", LGREY))
            c.setStrokeColor(g.get("stroke", MGREY))
            c.setLineWidth(0.8)
            if g.get("dashed"):
                c.setDash(3, 2)
            c.roundRect(g["x"], g["y"], g["w"], g["h"], 6, stroke=1, fill=1)
            c.setDash()
            if g.get("title"):
                c.setFillColor(g.get("tc", GREY))
                c.setFont("Body-Bold", g.get("fs", 8))
                c.drawString(g["x"] + 6, g["y"] + g["h"] - 11, g["title"])
        for a in self.arrows:
            pts = [self._anchor(p) for p in a["pts"]]
            col = a.get("color", GREY)
            c.setStrokeColor(col)
            c.setLineWidth(a.get("lw", 1.1))
            if a.get("dashed"):
                c.setDash(3, 2)
            p = c.beginPath()
            p.moveTo(*pts[0])
            for q in pts[1:]:
                p.lineTo(*q)
            c.drawPath(p, stroke=1, fill=0)
            c.setDash()
            self._head(c, *pts[-2], *pts[-1], col)
            if a.get("both"):
                self._head(c, *pts[1], *pts[0], col)
            if a.get("label"):
                # midpoint of the longest segment
                best = max(range(len(pts) - 1), key=lambda i: math.dist(pts[i], pts[i + 1]))
                mx = (pts[best][0] + pts[best + 1][0]) / 2 + a.get("dx", 0)
                my = (pts[best][1] + pts[best + 1][1]) / 2 + a.get("dy", 0)
                fs = a.get("fs", 6.8)
                tw = pdfmetrics.stringWidth(a["label"], "Body-Italic", fs)
                c.setFillColor(colors.white)
                c.rect(mx - tw / 2 - 2, my - fs / 2 - 1.5, tw + 4, fs + 3, stroke=0, fill=1)
                c.setFillColor(col)
                c.setFont("Body-Italic", fs)
                c.drawCentredString(mx, my - fs / 2 + 1, a["label"])
        for b in self.boxes.values():
            fill = b.get("fill", colors.white)
            stroke = b.get("stroke", BLUE)
            c.setFillColor(fill)
            c.setStrokeColor(stroke)
            c.setLineWidth(b.get("lw", 1))
            if b.get("dashed"):
                c.setDash(3, 2)
            if b.get("shape") == "circle":
                c.ellipse(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"], stroke=1, fill=1)
            else:
                c.roundRect(b["x"], b["y"], b["w"], b["h"], b.get("r", 5), stroke=1, fill=1)
            c.setDash()
            fs = b.get("fs", 8)
            st = ParagraphStyle("d", parent=S["diag"], fontSize=fs, leading=fs * 1.22,
                                textColor=b.get("tc", INK),
                                fontName="Body-Bold" if b.get("bold") else "Body")
            para = Paragraph(b["text"], st)
            pw, ph = para.wrap(b["w"] - 6, b["h"])
            para.drawOn(c, b["x"] + 3, b["y"] + (b["h"] - ph) / 2)
        for t in self.texts:
            c.setFillColor(t.get("color", GREY))
            c.setFont("Body-Bold" if t.get("bold") else "Body", t.get("fs", 8))
            fn = {"left": c.drawString, "center": c.drawCentredString,
                  "right": c.drawRightString}[t.get("anchor", "left")]
            fn(t["x"], t["y"], t["text"])


def centered(flowable):
    t = Table([[flowable]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def bx(x, y, w, h, text, fill=colors.white, stroke=BLUE, **kw):
    d = dict(x=x, y=y, w=w, h=h, text=text, fill=fill, stroke=stroke)
    d.update(kw)
    return d


# ---------------------------------------------------------------- document
class Doc(BaseDocTemplate):
    def __init__(self, path, title, subtitle, tag, **kw):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN + 6, bottomMargin=MARGIN, title=title,
                         author="EarthSleuth team", **kw)
        self.doc_title, self.doc_sub, self.doc_tag = title, subtitle, tag
        frame = Frame(MARGIN, MARGIN, CONTENT_W, PAGE_H - 2 * MARGIN - 6, id="f")
        self.addPageTemplates([
            PageTemplate("cover", frames=[frame], onPage=self._cover),
            PageTemplate("normal", frames=[frame], onPage=self._normal),
        ])

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("H1", "H2"):
            lvl = 0 if fl.style.name == "H1" else 1
            text = fl.getPlainText()
            key = "k%d" % id(fl)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=lvl, closed=lvl > 0)
            self.notify("TOCEntry", (lvl, text, self.page, key))

    def _normal(self, c, doc):
        c.saveState()
        c.setStrokeColor(MGREY)
        c.setLineWidth(0.5)
        c.line(MARGIN, PAGE_H - MARGIN + 4, PAGE_W - MARGIN, PAGE_H - MARGIN + 4)
        c.setFont("Body-Bold", 7.5)
        c.setFillColor(NAVY)
        c.drawString(MARGIN, PAGE_H - MARGIN + 9, "EarthSleuth")
        c.setFont("Body", 7.5)
        c.setFillColor(GREY)
        c.drawString(MARGIN + 46, PAGE_H - MARGIN + 9, "\u00b7  " + self.doc_tag)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 9,
                          "Team document \u00b7 NASA Space Apps Challenge 2026")
        c.line(MARGIN, MARGIN - 14, PAGE_W - MARGIN, MARGIN - 14)
        c.drawRightString(PAGE_W - MARGIN, MARGIN - 26, "Page %d" % doc.page)
        c.drawString(MARGIN, MARGIN - 26, "Working name \u201cEarthSleuth\u201d \u2014 rename freely")
        c.restoreState()

    def _cover(self, c, doc):
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, PAGE_H - 330, PAGE_W, 330, stroke=0, fill=1)
        # decorative orbit rings
        c.setStrokeColor(colors.HexColor("#2D4E7E"))
        c.setLineWidth(1)
        for r in (60, 95, 130, 165):
            c.circle(PAGE_W - 90, PAGE_H - 120, r, stroke=1, fill=0)
        c.setFillColor(colors.HexColor("#3FA7D6"))
        c.circle(PAGE_W - 90, PAGE_H - 120, 34, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#5CC48F"))
        c.circle(PAGE_W - 100, PAGE_H - 112, 14, stroke=0, fill=1)
        c.circle(PAGE_W - 76, PAGE_H - 132, 9, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.circle(PAGE_W - 90 + 95 * math.cos(2.3), PAGE_H - 120 + 95 * math.sin(2.3), 5,
                 stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#9FC3EA"))
        c.setFont("Body-Bold", 10)
        c.drawString(MARGIN, PAGE_H - 70, self.doc_tag.upper())
        c.setFillColor(colors.white)
        c.setFont("Body-Bold", 34)
        c.drawString(MARGIN, PAGE_H - 125, "EarthSleuth")
        c.setFont("Body", 15)
        y = PAGE_H - 160
        for line in self.doc_title.split("\n"):
            c.drawString(MARGIN, y, line)
            y -= 20
        c.setFillColor(colors.HexColor("#C8D8EE"))
        c.setFont("Body", 10.5)
        y -= 8
        for line in self.doc_sub.split("\n"):
            c.drawString(MARGIN, y, line)
            y -= 15
        c.setFillColor(GREY)
        c.setFont("Body", 8.5)
        c.drawString(MARGIN, 40, "NASA Space Apps Challenge 2026 \u00b7 Internal team document \u00b7 "
                                 "\u201cEarthSleuth\u201d is a working name")
        c.drawRightString(PAGE_W - MARGIN, 40, "November 14, 2026")
        c.restoreState()

    def build_story(self, story):
        # never leave a heading alone at the bottom of a page
        from reportlab.platypus import CondPageBreak

        def is_head(f):
            return isinstance(f, Paragraph) and f.style.name in ("H1", "H2", "H3")
        out = []
        for i, f in enumerate(story):
            if is_head(f) and not (i and is_head(story[i - 1])):
                out.append(CondPageBreak(200))
            out.append(f)
        self.multiBuild(out)


def toc():
    t = TableOfContents()
    t.levelStyles = [S["toc1"], S["toc2"]]
    t.dotsMinLevel = 0
    return t
