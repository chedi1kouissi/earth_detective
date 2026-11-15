"""Content shared by both documents: the problem, the challenge, glossary, common diagrams."""
from common import *  # noqa: F401,F403


# ------------------------------------------------------------------ diagrams
def diagram_opposite():
    W, H = 470, 165
    boxes = {
        "cause": bx(160, 112, 150, 42, "<b>One cause</b><br/>the planet gets warmer",
                    fill=CREAM, stroke=ORANGE),
        "wet": bx(10, 18, 190, 56, "<b>Region A (already wet)</b><br/>warmer air holds more water "
                  "→ heavier rain<br/><font color='#138A7E'><b>rainfall ↑</b></font>",
                  fill=TEAL_L, stroke=TEAL),
        "dry": bx(270, 18, 190, 56, "<b>Region B (already dry)</b><br/>more evaporation, shifted "
                  "storm tracks<br/><font color='#C8423B'><b>rainfall ↓</b></font>",
                  fill=ROSE, stroke=RED),
    }
    arrows = [
        dict(pts=[("cause", "bottom", 0.3), ("wet", "top", 0.6)], color=TEAL),
        dict(pts=[("cause", "bottom", 0.7), ("dry", "top", 0.4)], color=RED),
    ]
    return centered(Diagram(W, H, boxes, arrows))


def diagram_stats_pipeline(compact=False):
    W, H = 495, 190
    steps = [
        ("1", "Pick a region<br/>& cut it into<br/>grid cells"),
        ("2", "Build a monthly<br/>time series<br/>for each cell"),
        ("3", "Remove the<br/>seasons<br/>(anomalies)"),
        ("4", "Measure the<br/>slope<br/>(Theil–Sen)"),
        ("5", "Test it<br/>(Mann–Kendall,<br/>autocorr. fix)"),
        ("6", "Add a<br/>confidence<br/>interval"),
        ("7", "Fix the ‘many<br/>tests’ problem<br/>(FDR)"),
        ("8", "Save result<br/>+ provenance<br/>to graph"),
    ]
    boxes, arrows = {}, []
    bw, bh, gap = 104, 62, 26
    for i, (n, t) in enumerate(steps):
        row = 0 if i < 4 else 1
        col = i if i < 4 else 7 - i   # snake layout
        x = 8 + col * (bw + gap)
        y = 112 if row == 0 else 18
        fill = SKY if i < 3 else (TEAL_L if i < 7 else LILAC)
        stroke = BLUE if i < 3 else (TEAL if i < 7 else PURPLE)
        boxes[n] = bx(x, y, bw, bh, "<b>Step %s</b><br/>%s" % (n, t), fill=fill, stroke=stroke)
    for i in range(1, 8):
        a, b = str(i), str(i + 1)
        if i < 4:
            arrows.append(dict(pts=[(a, "right"), (b, "left")]))
        elif i == 4:
            arrows.append(dict(pts=[(a, "bottom"), (b, "top")]))
        else:
            arrows.append(dict(pts=[(a, "left"), (b, "right")]))
    texts = [dict(x=8, y=180, text="Prepare the data", fs=7.5, color=BLUE, bold=True),
             dict(x=8 + 3 * (bw + gap), y=180, text="Statistics", fs=7.5, color=TEAL, bold=True)]
    return centered(Diagram(W, H, boxes, arrows, texts=texts))


# ------------------------------------------------------------------ sections
def problem_section(story):
    story.append(H1("1. The problem, explained simply"))
    story.append(P(
        "Before we talk about software, we all need to understand the science problem in the same way. "
        "This section uses no jargon. Every technical word we use later is also explained in the "
        "glossary at the end of this document."))

    story.append(H2("1.1 The Earth is always changing"))
    story.append(P(
        "The Earth is like a giant machine with many connected parts: the air (atmosphere), the oceans, "
        "the land, the ice and all living things. When one part changes, other parts react. If the air "
        "gets warmer, more water evaporates from the soil. If the soil dries out, plants get stressed. "
        "If plants die, the ground gets darker and absorbs more sunlight, which makes it even warmer."))
    story.append(P(
        "Some changes are short (a hot week, one rainy month). Others keep going in the same direction "
        "for many years: rising, falling, thickening, thinning. Scientists care a lot about these "
        "long, one-direction changes because they tell us <b>what processes are at work</b> and "
        "<b>what will be affected next</b>."))

    story.append(H2("1.2 How do we watch the Earth?"))
    story.append(P("There are two main sources of information, and our tool uses both:"))
    story.append(bullets([
        "<b>Satellites (observations).</b> NASA satellites carry <b>instruments</b> that measure "
        "things from space every day: surface temperature, rainfall, vegetation, ozone, water vapour... "
        "Examples: MODIS (on the Terra and Aqua satellites), GPM (rain), AIRS (temperature and humidity "
        "in the air), OMI (ozone and air pollution).",
        "<b>Models (computer simulations fed with observations).</b> Some things are hard to measure "
        "directly everywhere, like how wet the soil is one metre down, or how much water evaporates. "
        "Scientists build computer models of the Earth and feed them real observations so the model "
        "stays close to reality. The result looks like a complete, gap-free map of the Earth for every "
        "day or month. Examples: <b>MERRA-2</b> (the atmosphere) and <b>GLDAS</b> (land and water).",
    ]))
    story.append(box("kid", [
        "Imagine you want to know whether your town is getting hotter. A satellite is like a friend "
        "who takes a photo of your town from the sky every single day for 25 years. A model is like a "
        "very smart notebook that fills in the days your friend missed and also guesses things the "
        "photo can't show directly (like how wet the ground is underneath)."]))

    story.append(H2("1.3 What is a “variable” and what is a “time series”?"))
    story.append(P(
        "A <b>variable</b> is one thing that gets measured, with a unit. Examples: air temperature "
        "(in °C or Kelvin), precipitation, which means rain + snow (in mm per month), soil moisture "
        "(kg of water per m²), vegetation greenness (NDVI, a number between −1 and 1)."))
    story.append(P(
        "A <b>time series</b> is the list of values of one variable, at one place, over time. If we "
        "take the average temperature of Tunisia for every month from January 2001 to December 2024, we "
        "get 288 numbers in a row. Plot them and you get a wiggly line. That line is the time series."))
    story.append(P(
        "Satellite and model data come as <b>grids</b>: the world is cut into little squares "
        "(called <b>grid cells</b> or <b>pixels</b>), for example 0.25° × 0.25° "
        "(about 28 km × 28 km at the equator). Every square has its own value for every day or "
        "month. So each square has its own time series."))

    story.append(H2("1.4 What is a “trend”?"))
    story.append(P(
        "A <b>trend</b> is the general direction of a time series over a long time, ignoring the "
        "small ups and downs. We usually describe it with a straight line and give its <b>slope</b>: "
        "“+0.4 °C per decade” means that, on average, temperature went up by 0.4 "
        "degrees every 10 years."))
    story.append(box("kid", [
        "Think of your height. If someone measured you every month, the numbers would wiggle a bit "
        "(shoes on, shoes off, morning or evening). But over the years the general direction is clearly "
        "up. That general direction is the trend. The wiggles are called <b>noise</b>."]))

    story.append(H2("1.5 Why is finding trends hard? Four reasons"))
    story.append(H3("Reason 1: there are far too many variables"))
    story.append(P(
        "NASA and other agencies publish thousands of datasets with tens of thousands of variables. "
        "Some have easy names (“precipitation”), others are very specialised "
        "(“SoilMoi0_10cm_inst”, “Evap_tavg”). A student does not know which ones "
        "to look at, where they are, or what they mean."))
    story.append(H3("Reason 2: the same cause can push in opposite directions"))
    story.append(P(
        "This is the special twist of this challenge. One process can make a variable go <b>up in one "
        "region and down in another</b>. If you average over a big area, the two can cancel out and you "
        "see “no change”, even though both places are changing a lot."))
    story.append(diagram_opposite())
    story.append(caption("Figure 1. The same process (warming) can push rainfall up in one place and down "
                         "in another. Scientists sometimes summarise this as “wet gets wetter, dry "
                         "gets drier” (a simplification, but a useful one)."))
    story.append(H3("Reason 3: seasons and noise hide the trend"))
    story.append(P(
        "Every year, summer is hot and winter is cold. That seasonal swing (often 15–20 °C) is "
        "tens of times bigger than a climate trend (a few tenths of a degree per decade). If we don't remove the seasons first, the trend is buried. Random "
        "weather (one very wet year, one dry year) also adds noise."))
    story.append(H3("Reason 4: “Is it real or just luck?”"))
    story.append(P(
        "Even random numbers can look like they go up for a while. So scientists ask whether a trend is "
        "<b>statistically significant</b>. This is the most important idea in the whole challenge, so "
        "it gets its own section."))

    story.append(H2("1.6 What does “significant” mean?"))
    story.append(P(
        "A trend is <b>significant</b> when it is very unlikely that random noise alone would have "
        "produced it. We measure this with a number called the <b>p-value</b>."))
    story.append(bullets([
        "The <b>p-value</b> answers: <i>“If there were really no trend, how often would random "
        "luck produce a trend at least this strong?”</i>",
        "A small p-value (for example 0.01 = 1%) means “this would almost never happen by luck”, "
        "so we believe the trend is real.",
        "Scientists usually pick a threshold called <b>alpha (α)</b>, often 0.05. If p &lt; 0.05 "
        "we call the trend significant.",
        "A <b>confidence interval</b> gives a range for the slope: “the trend is +0.4 °C per "
        "decade, and we are 95% confident the true value is between +0.2 and +0.6”. If the range "
        "does not include zero, the direction of the trend is trustworthy.",
    ]))
    story.append(box("kid", [
        "You flip a coin 10 times and get 7 heads. Is the coin broken? Probably not: that happens "
        "fairly often by luck (about 17% of the time, so p ≈ 0.17). Now you flip it 100 times and get "
        "70 heads. That almost never happens with a fair coin (p is tiny), so you would say the coin is "
        "“significantly” unfair. Trends work the same way: <b>more data makes it easier to "
        "be sure</b>.",
        "This is why the challenge says a trend that is not significant is still interesting: "
        "sometimes it only needs <b>more years of data</b> to become significant."]))


def challenge_section(story):
    story.append(H1("2. The challenge NASA gave us"))
    story.append(H2("2.1 The challenge in one sentence"))
    story.append(box("note", [
        "Build a tool that can <b>select</b> variables measured by Earth science missions or produced by "
        "models, <b>visualise</b> how they change over time, and determine <b>what</b> is changing, "
        "<b>where</b> it is changing, <b>how much</b> it is changing, and whether the change is "
        "<b>statistically significant</b>."], title="The challenge"))
    story.append(H2("2.2 The four official objectives"))
    story.append(table([
        ["#", "What NASA wrote (summary)", "What it means in plain words", "What we must build"],
        ["1", "Identify Earth science variables of interest that can be investigated for trends.",
         "Help people find which measurements are worth looking at.",
         "A variable finder: search by topic / question, simple definitions, suggestions."],
        ["2", "Acquire the data variables for a particular region.",
         "Get the numbers for one place, because most trends are regional.",
         "Region picker + automatic download / subsetting of NASA data."],
        ["3", "Generate and visualise a time series over a long enough period.",
         "Draw the wiggly line over many years (enough years for statistics).",
         "Time-series charts and maps."],
        ["4", "Perform a basic statistical analysis: rate of change and significance (t-test, "
              "Mann–Kendall, confidence intervals).",
         "Say how fast it changes and whether it is real or luck.",
         "A statistics engine: slope, p-value, confidence interval."],
    ], [0.3, 2.2, 2.0, 2.1]))
    story.append(P("NASA says that a project that does <b>both</b> the visualisation and the "
                   "statistical analysis <b>meets the full scope</b> of the challenge. Everything else "
                   "we add is how we stand out."))
    story.append(H2("2.3 Who the tool is for"))
    story.append(bullets([
        "High-school and university students, and members of the public with some science background.",
        "They need <b>simple definitions</b> of each variable.",
        "The idea is to turn them into <b>“data detectives”</b>: find a variable of interest, "
        "check whether it shows a trend, and check whether the trend is significant.",
    ]))
    story.append(H2("2.4 Extra ideas NASA suggests (optional, but they hint at what judges like)"))
    story.append(bullets([
        "Ask the user a <b>short series of questions</b> (what? where?) and use the answers to find "
        "related variables.",
        "Provide <b>a couple of demonstration examples</b> the user can watch to learn the tool.",
        "Use <b>SI (AI)</b> to suggest data likely to show trends in a place, using news, research "
        "papers, or the type of region (desert, rainforest, estuary, the air above a big city).",
        "Daily and monthly data are the easiest to process.",
        "A trend that is not significant is still interesting; it may need a longer record.",
        "Look at outside tools such as CUAHSI (hydrology).",
        "Seasonal cycles may need to be removed; linear trends are enough for this challenge.",
    ]))
    story.append(H2("2.5 How the judges will score us"))
    story.append(P("Each project gets a score from 1 to 5 on five criteria (5 is best):"))
    story.append(table([
        ["Criterion", "Question the judges ask", "How we earn a 5"],
        ["Impact", "How big is the problem and how many people does it help?",
         "Students and the public can investigate real Earth changes on their own; show who benefits."],
        ["Creativity", "How original is the idea?",
         "Automatic discovery of trends, opposite-trend maps, an evidence graph and an AI investigator, "
         "instead of yet another chart tool."],
        ["Validity", "Would it really work? Scientifically sound, feasible, easy to use?",
         "Correct statistics (seasons removed, autocorrelation handled, multiple-testing correction), "
         "and a working demo."],
        ["Relevance", "Does it answer the challenge, with NASA data at its core?",
         "Every finding is computed from real NASA data (MERRA-2, GPM, GLDAS, MODIS...)."],
        ["Presentation", "Is the story clear and engaging?",
         "One short, visual investigation: from a vague question to a tested, explained trend."],
    ], [1.1, 2.3, 3.6]))
    story.append(box("warn", [
        "<b>Submission rules we must respect:</b> a demo that is either a video of 30 seconds or less "
        "<b>or</b> a deck of at most 7 slides (the title slide counts), in English or subtitled; a "
        "public link that needs no login; a 50–200 word summary; at least one NASA data source "
        "(required for global awards); links to every data source and resource used; no NASA logos, "
        "flags or mission insignia in anything we generate; say where we used AI tools; no names, "
        "voices or faces of anyone under 18."], title="Submission rules"))


GLOSSARY = [
    ("Agent (AI agent)", "An AI program that does not just answer; it plans steps and calls tools "
     "(functions, databases, APIs) to finish a task."),
    ("Alpha (α)", "The p-value threshold below which we call a result significant (often 0.05)."),
    ("Anomaly", "How far a value is from “normal” for that time of year. "
     "July anomaly = this July minus the average July."),
    ("Autocorrelation", "When this month's value looks like last month's value. It makes data look "
     "more certain than it is, so tests must correct for it."),
    ("Benjamini–Hochberg (FDR)", "A method that controls the share of false discoveries when "
     "running many tests (for example one test per grid cell)."),
    ("CF Standard Names", "An agreed list of official names and units for climate variables, e.g. "
     "“air_temperature”, “precipitation_flux”. Helps match variables across datasets."),
    ("Change point", "A moment where a time series suddenly changes behaviour (level or slope)."),
    ("Clustering", "A machine-learning method that groups similar things together without being told "
     "the groups in advance (e.g. k-means, HDBSCAN)."),
    ("CMR", "NASA's Common Metadata Repository: the catalogue (search engine) of all NASA Earth "
     "science datasets."),
    ("Confidence interval", "A range that probably contains the true value (e.g. 95% CI)."),
    ("Cypher", "The query language of the Neo4j graph database."),
    ("Dataset / collection", "A product published by NASA, e.g. “GLDAS_NOAH025_M”. "
     "It contains several variables."),
    ("Earthdata Login", "The free NASA account needed to download most data."),
    ("Embedding", "A list of numbers that represents the meaning of a text so a computer can find "
     "similar texts."),
    ("Evapotranspiration (ET)", "Water going from the ground and plants into the air "
     "(evaporation + plant “sweating”)."),
    ("GLDAS", "Global Land Data Assimilation System: a NASA land model giving soil moisture, ET, runoff..."),
    ("GNN", "Graph Neural Network: a neural network that learns from data arranged as a graph."),
    ("GPM / IMERG", "Global Precipitation Measurement mission; IMERG is its merged rainfall product."),
    ("Granule", "One file of a dataset (for example one month)."),
    ("Graph (knowledge graph)", "Data stored as things (nodes) connected by named relationships (edges)."),
    ("GraphRAG", "Retrieval-Augmented Generation using a graph: the AI looks up connected facts "
     "in the graph before answering."),
    ("Grid cell", "One small square of a gridded map; it has its own time series."),
    ("Hallucination", "When an AI states something false with confidence."),
    ("Hamed–Rao correction", "A fix to the Mann–Kendall test that accounts for autocorrelation."),
    ("LLM", "Large Language Model: the AI that reads and writes text (e.g. Claude, GPT, Gemini)."),
    ("Mann–Kendall test", "A test that checks whether values tend to go up (or down) over time, "
     "by counting ups and downs. Does not need a bell-shaped distribution."),
    ("MERRA-2", "NASA's reanalysis of the atmosphere since 1980 (temperature, wind, humidity...)."),
    ("MODIS", "An instrument on the Terra and Aqua satellites; gives land temperature, vegetation (NDVI)..."),
    ("NDVI", "Normalized Difference Vegetation Index: how green / alive vegetation is (−1 to 1)."),
    ("NetCDF / HDF / Zarr", "File formats for gridded science data (think: spreadsheets with many "
     "dimensions: time × latitude × longitude)."),
    ("Neo4j", "A popular graph database."),
    ("Node / Edge", "In a graph: a node is a thing, an edge is a named link between two things."),
    ("Noise", "Random ups and downs that hide the signal."),
    ("p-value", "The probability of seeing a trend this strong if there were no real trend."),
    ("Provenance", "The full record of where a result came from: data, version, region, method, code."),
    ("Reanalysis", "A model run that is constantly corrected by observations, giving complete maps."),
    ("Regridding", "Converting data from one grid to another so different datasets line up."),
    ("Seasonal cycle", "The repeating yearly pattern (summer/winter). We remove it before testing trends."),
    ("Significant", "Unlikely to be caused by random luck alone (p below alpha)."),
    ("Slope", "How fast the trend line goes up or down (e.g. +0.3 °C per decade)."),
    ("Soil moisture", "How much water is in the soil."),
    ("Theil–Sen slope", "A robust slope: the median of the slopes between all pairs of points."),
    ("Time series", "The values of one variable at one place over time."),
    ("Trend", "The long-term direction of a time series."),
]


def glossary_section(story, num, extra=()):
    story.append(H1("%s. Glossary (all the words in one place)" % num))
    items = sorted(list(GLOSSARY) + list(extra), key=lambda kv: kv[0].lower())
    rows = [["Word", "Simple meaning"]] + [[f"<b>{a}</b>", b] for a, b in items]
    story.append(table(rows, [1.6, 5.4], font=8.4))
