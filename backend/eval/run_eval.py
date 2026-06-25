"""LaunchLens evaluation harness (DeepEval) — agent-answer evaluation.

Runs the REAL agent (live SerpApi + Oxylabs + LLM) on the golden dataset, then scores
each answer with LLM-judge metrics appropriate to its intent, and writes a results
TABLE to eval_results.md (incrementally, so partial runs are saved).

Metrics:
  • VerdictQuality (G-Eval) — clear GO/NO-GO/NICHE covering demand, price band,
    differentiation, positioning, grounded in the retrieved data.   [fusion only]
  • DataFusion (G-Eval)     — the verdict genuinely uses BOTH demand (Google) and
    supply (Amazon) evidence — the core thesis of LaunchLens.        [fusion only]
  • Faithfulness            — claims grounded in the live demand/supply data
    (catches invented complaints / hallucinated numbers).           [data-backed intents]
  • AnswerRelevancy         — actually addresses the founder's question.   [all]

Run:
  uv run --with deepeval python backend/eval/run_eval.py            # full 50
  uv run --with deepeval python backend/eval/run_eval.py --ids 1,6  # subset
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from langchain_core.messages import HumanMessage

from launchlens import config, memory  # noqa: F401  (loads .env so the judge sees OPENAI_API_KEY)
from launchlens.graph import build_graph

from golden_queries import GOLDEN  # noqa: E402

from deepeval.metrics import (  # noqa: E402
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams  # noqa: E402

JUDGE_MODEL = "gpt-4o-mini"
HERE = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(HERE, "eval_results.md")
VERDICT_RE = re.compile(r"NO[\s-]?GO|NICHE|\bGO\b", re.I)

DATA_INTENTS = {"fusion", "demand", "pricing", "reviews", "compare"}


def run_agent(graph, item, thread_id):
    cfg = {"configurable": {"thread_id": thread_id}}
    answer = ""
    for chunk in graph.stream({"messages": [HumanMessage(content=item["query"])], "domain": item["market"]},
                              cfg, stream_mode="updates"):
        for node, upd in chunk.items():
            if node == "agent" and upd and not getattr(upd["messages"][-1], "tool_calls", None):
                answer = upd["messages"][-1].content
    vals = graph.get_state(cfg).values
    ctx = [json.dumps(s, ensure_ascii=False)
           for s in vals.get("demand_signals", []) + vals.get("supply_signals", [])
           if not s.get("error")]
    return answer, ctx


def extract_verdict(answer):
    m = VERDICT_RE.search(answer or "")
    if not m:
        return "—"
    return re.sub(r"\s+", "-", m.group(0).upper()).replace("--", "-")


def main():
    args = sys.argv[1:]
    if "--ids" in args:
        wanted = {int(x) for x in args[args.index("--ids") + 1].split(",")}
        items = [q for q in GOLDEN if q["id"] in wanted]
    else:
        items = GOLDEN

    graph = build_graph(memory.get_checkpointer(), memory.get_store())

    verdict_metric = GEval(
        name="VerdictQuality",
        criteria=("The answer gives a clear GO / NO-GO / NICHE verdict and covers demand, "
                  "price band, differentiation, and positioning, citing concrete numbers "
                  "drawn from the retrieved demand/supply context."),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT,
                           LLMTestCaseParams.RETRIEVAL_CONTEXT],
        model=JUDGE_MODEL, threshold=0.6,
    )
    fusion_metric = GEval(
        name="DataFusion",
        criteria=("The verdict genuinely fuses BOTH sides of evidence: demand signals from "
                  "Google (trend direction, related searches, shopping price band, news) AND "
                  "supply signals from Amazon (what's selling, competitor prices, review "
                  "complaints). Penalise answers that lean on only one side."),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT,
                           LLMTestCaseParams.RETRIEVAL_CONTEXT],
        model=JUDGE_MODEL, threshold=0.6,
    )
    faithfulness = FaithfulnessMetric(threshold=0.5, model=JUDGE_MODEL)
    relevancy = AnswerRelevancyMetric(threshold=0.5, model=JUDGE_MODEL)

    def metrics_for(cat):
        if cat == "fusion":
            return [("VerdictQuality", verdict_metric), ("DataFusion", fusion_metric),
                    ("Faithfulness", faithfulness), ("Relevancy", relevancy)]
        if cat in DATA_INTENTS:
            return [("Faithfulness", faithfulness), ("Relevancy", relevancy)]
        return [("Relevancy", relevancy)]

    cols = ["VerdictQuality", "DataFusion", "Faithfulness", "Relevancy"]
    md = open(MD_PATH, "w", encoding="utf-8")
    md.write("# LaunchLens — Evaluation Results (DeepEval, live agent)\n\n")
    md.write("Each row is a real agent run scored by LLM-judge metrics (0–1, higher is better). "
             "Verdict = the GO/NO-GO/NICHE the agent returned. "
             "Blank cells = metric not applicable to that intent.\n\n")
    md.write("| ID | Intent | Market | Verdict | " + " | ".join(cols) + " | Query |\n")
    md.write("|---|---|---|---|" + "|".join(["---"] * len(cols)) + "|---|\n")

    print(f"Evaluating {len(items)} queries (live)...\n")
    sums = {c: [0.0, 0] for c in cols}
    for it in items:
        tid = f"eval-{it.get('thread', it['id'])}"
        try:
            answer, ctx = run_agent(graph, it, tid)
        except Exception as exc:  # noqa: BLE001
            answer, ctx = f"(agent error: {exc})", []
        verdict = extract_verdict(answer) if it["category"] in ("fusion", "followup") else "—"
        tc = LLMTestCase(input=it["query"], actual_output=answer or "(empty)",
                         retrieval_context=ctx or ["(no data)"], context=ctx or ["(no data)"])
        scores = {c: "" for c in cols}
        for name, metric in metrics_for(it["category"]):
            try:
                metric.measure(tc)
                scores[name] = f"{metric.score:.2f}"
                sums[name][0] += metric.score
                sums[name][1] += 1
            except Exception as exc:  # noqa: BLE001
                scores[name] = f"err"
                print(f"   metric {name} failed on #{it['id']}: {exc}")
        row_scores = [scores[c] for c in cols]
        md.write(f"| {it['id']} | {it['category']} | {it['market']} | {verdict} | "
                 + " | ".join(s or '·' for s in row_scores)
                 + f" | {it['query'][:60]} |\n")
        md.flush()
        print(f"[{it['id']:>2}] {it['category']:<8} {verdict:<6} "
              + "  ".join(f"{c}={scores[c] or '-'}" for c in cols))

    md.write("\n## Averages\n\n| Metric | Mean | N |\n|---|---|---|\n")
    print("\n=== Averages ===")
    for c in cols:
        tot, n = sums[c]
        mean = (tot / n) if n else 0.0
        md.write(f"| {c} | {mean:.2f} | {n} |\n")
        print(f"  {c:<15} {mean:.2f}  (n={n})")
    md.close()
    print(f"\nSaved table -> {MD_PATH}")
    memory.close()


if __name__ == "__main__":
    main()
