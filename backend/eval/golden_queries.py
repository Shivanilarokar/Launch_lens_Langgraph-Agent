"""LaunchLens golden evaluation dataset — 50 fusion launch-decision queries.

LaunchLens' core job is the FUSION VERDICT: fuse demand (Google:
Trends / Shopping / News) with supply (Amazon: what's selling, at what price, with
what review complaints) into a clear GO / NO-GO / NICHE call a founder can act on.

So every query here is a real founder launch decision. They vary across:
  • category  — 50 distinct product ideas
  • market    — India (in) / US (com) / UK (co.uk)
  • price     — sub-₹500 to ₹5000, $5 to $150, £12 to £60
  • phrasing  — "should I launch", "is it worth", "can I make money", "good bet",
                "thinking of selling", "is there room for" … (verdict logic must hold
                regardless of sentence shape)

`expects` notes what a good verdict must contain; for fusion that ALWAYS means a
GO/NO-GO/NICHE call grounded in BOTH demand and supply evidence.
"""

GOLDEN = [
    {"id": 1,  "category": "fusion", "market": "in",    "query": "Should I launch a stainless steel insulated water bottle in India under ₹1,500?", "expects": "verdict grounded in demand trend + Amazon price band vs ₹1500 + review gaps + positioning"},
    {"id": 2,  "category": "fusion", "market": "com",   "query": "Is it worth launching a bamboo cutting board in the US under $25?", "expects": "verdict + demand + price band vs $25 + differentiation"},
    {"id": 3,  "category": "fusion", "market": "in",    "query": "Should I launch a cork yoga mat in India under ₹1,200?", "expects": "verdict + demand + price band + gaps"},
    {"id": 4,  "category": "fusion", "market": "com",   "query": "Thinking of selling a portable blender in the US around $40 — good bet?", "expects": "verdict + demand + price band"},
    {"id": 5,  "category": "fusion", "market": "in",    "query": "Can I make money launching a ceramic non-stick frying pan in India under ₹1,200?", "expects": "verdict + review gaps + price band"},
    {"id": 6,  "category": "fusion", "market": "co.uk", "query": "Is a matcha starter kit worth launching in the UK under £30?", "expects": "verdict + rising demand + supply saturation"},
    {"id": 7,  "category": "fusion", "market": "in",    "query": "Should I launch reusable silicone food storage bags in India under ₹800?", "expects": "verdict + price band + gaps"},
    {"id": 8,  "category": "fusion", "market": "com",   "query": "Is it a good idea to sell a magnetic phone mount in the US under $20?", "expects": "verdict + saturation read"},
    {"id": 9,  "category": "fusion", "market": "in",    "query": "Should I launch an LED ring light for creators in India under ₹2,000?", "expects": "verdict + demand + price band"},
    {"id": 10, "category": "fusion", "market": "com",   "query": "Is a collapsible silicone travel mug worth launching in the US under $20?", "expects": "verdict + review gaps"},
    {"id": 11, "category": "fusion", "market": "com",   "query": "Should I launch a bamboo toothbrush in the US under $5?", "expects": "verdict + saturation (likely no-go/niche)"},
    {"id": 12, "category": "fusion", "market": "com",   "query": "Is it worth launching a standing desk converter in the US under $150?", "expects": "verdict + price band + demand"},
    {"id": 13, "category": "fusion", "market": "co.uk", "query": "Should I launch a weighted blanket in the UK under £60?", "expects": "verdict + demand + gaps"},
    {"id": 14, "category": "fusion", "market": "in",    "query": "Is an electric milk frother worth launching in India under ₹1,500?", "expects": "verdict + price band"},
    {"id": 15, "category": "fusion", "market": "com",   "query": "Should I launch a pet grooming glove in the US under $15?", "expects": "verdict + review gaps"},
    {"id": 16, "category": "fusion", "market": "in",    "query": "Is an insulated office lunch box worth launching in India under ₹900?", "expects": "verdict + price band"},
    {"id": 17, "category": "fusion", "market": "in",    "query": "Should I launch wireless earbuds in India under ₹1,500?", "expects": "verdict + heavy saturation read"},
    {"id": 18, "category": "fusion", "market": "com",   "query": "Is a resistance bands set worth launching in the US under $25?", "expects": "verdict + gaps"},
    {"id": 19, "category": "fusion", "market": "in",    "query": "Should I launch a ceramic coffee mug in India under ₹600?", "expects": "verdict + price band"},
    {"id": 20, "category": "fusion", "market": "co.uk", "query": "Is a reusable coffee cup worth launching in the UK under £15?", "expects": "verdict + demand + saturation"},
    {"id": 21, "category": "fusion", "market": "in",    "query": "Should I launch an air fryer in India under ₹5,000?", "expects": "verdict + demand + price band + review gaps"},
    {"id": 22, "category": "fusion", "market": "com",   "query": "Is a posture corrector worth launching in the US under $30?", "expects": "verdict + demand + gaps"},
    {"id": 23, "category": "fusion", "market": "in",    "query": "Should I launch a silk sleep mask in India under ₹500?", "expects": "verdict + price band"},
    {"id": 24, "category": "fusion", "market": "com",   "query": "Thinking of launching a jade facial roller in the US under $15 — worth it?", "expects": "verdict + saturation"},
    {"id": 25, "category": "fusion", "market": "in",    "query": "Is a protein shaker bottle worth launching in India under ₹400?", "expects": "verdict + price band + gaps"},
    {"id": 26, "category": "fusion", "market": "com",   "query": "Should I launch a foldable laundry basket in the US under $20?", "expects": "verdict + demand"},
    {"id": 27, "category": "fusion", "market": "co.uk", "query": "Is an electric kettle worth launching in the UK under £25?", "expects": "verdict + saturation read"},
    {"id": 28, "category": "fusion", "market": "in",    "query": "Should I launch a kids school backpack in India under ₹1,000?", "expects": "verdict + price band + brand competition"},
    {"id": 29, "category": "fusion", "market": "com",   "query": "Is a car phone holder worth launching in the US under $18?", "expects": "verdict + saturation"},
    {"id": 30, "category": "fusion", "market": "in",    "query": "Should I launch a beard trimmer in India under ₹1,200?", "expects": "verdict + demand + price band"},
    {"id": 31, "category": "fusion", "market": "com",   "query": "Is a scented soy candle set worth launching in the US under $25?", "expects": "verdict + demand + differentiation"},
    {"id": 32, "category": "fusion", "market": "in",    "query": "Should I launch a memory-foam pet bed in India under ₹1,500?", "expects": "verdict + price band + gaps"},
    {"id": 33, "category": "fusion", "market": "com",   "query": "Is a desk cable organizer worth launching in the US under $12?", "expects": "verdict + saturation"},
    {"id": 34, "category": "fusion", "market": "co.uk", "query": "Should I launch a bluetooth shower speaker in the UK under £20?", "expects": "verdict + demand + gaps"},
    {"id": 35, "category": "fusion", "market": "in",    "query": "Is a gaming mouse worth launching in India under ₹1,000?", "expects": "verdict + saturation read"},
    {"id": 36, "category": "fusion", "market": "com",   "query": "Should I launch a ceramic plant pot set in the US under $30?", "expects": "verdict + demand + price band"},
    {"id": 37, "category": "fusion", "market": "in",    "query": "Is a foldable travel toiletry bag worth launching in India under ₹700?", "expects": "verdict + gaps"},
    {"id": 38, "category": "fusion", "market": "com",   "query": "Should I launch a stainless steel straw set in the US under $10?", "expects": "verdict + saturation (likely no-go)"},
    {"id": 39, "category": "fusion", "market": "in",    "query": "Is a smart LED strip light worth launching in India under ₹800?", "expects": "verdict + demand + price band"},
    {"id": 40, "category": "fusion", "market": "co.uk", "query": "Should I launch a reusable beeswax food wrap in the UK under £12?", "expects": "verdict + demand + differentiation"},
    {"id": 41, "category": "fusion", "market": "in",    "query": "Is there room to launch a handheld neck massager in India under ₹2,000?", "expects": "verdict + demand + gaps"},
    {"id": 42, "category": "fusion", "market": "com",   "query": "Should I launch a silicone baking mat set in the US under $18?", "expects": "verdict + price band + saturation"},
    {"id": 43, "category": "fusion", "market": "in",    "query": "Is a memory-foam travel neck pillow worth launching in India under ₹800?", "expects": "verdict + gaps"},
    {"id": 44, "category": "fusion", "market": "com",   "query": "Thinking of launching an adjustable dumbbell set in the US under $120 — viable?", "expects": "verdict + demand + price band"},
    {"id": 45, "category": "fusion", "market": "co.uk", "query": "Should I launch a wooden phone stand in the UK under £12?", "expects": "verdict + saturation"},
    {"id": 46, "category": "fusion", "market": "in",    "query": "Is an electric spice grinder worth launching in India under ₹1,500?", "expects": "verdict + price band + gaps"},
    {"id": 47, "category": "fusion", "market": "com",   "query": "Should I launch reusable produce mesh bags in the US under $14?", "expects": "verdict + demand + differentiation"},
    {"id": 48, "category": "fusion", "market": "in",    "query": "Are blue-light blocking glasses worth launching in India under ₹1,000?", "expects": "verdict + demand + saturation"},
    {"id": 49, "category": "fusion", "market": "com",   "query": "Is a portable neck fan worth launching in the US under $25?", "expects": "verdict + demand + gaps"},
    {"id": 50, "category": "fusion", "market": "co.uk", "query": "Should I launch bamboo bed sheets in the UK under £45?", "expects": "verdict + price band + differentiation"},
]

CATEGORIES = sorted({q["category"] for q in GOLDEN})
FUSION = [q for q in GOLDEN if q["category"] == "fusion"]
