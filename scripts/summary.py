import json, os, statistics as st
BASE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(BASE, "..", "data", "results.jsonl"), encoding="utf-8")]
def acc(xs): return 100 * sum(x["correct"] for x in xs) / len(xs) if xs else float("nan")
rows = {}
for v in ["add_only", "add_delete"]:
    rv = [r for r in R if r["variant"] == v]
    use = [r for r in rv if r["type"] == "mem_use"]
    upd = [r for r in use if r["has_update"]]
    noupd = [r for r in use if not r["has_update"]]
    free = [r for r in rv if r["type"] == "mem_free"]
    base = acc([{"correct": r["baseline_correct"]} for r in free])
    rows[v] = {
        "mem_use_acc": acc(use), "mem_use_update_acc": acc(upd), "mem_use_noupdate_acc": acc(noupd),
        "mem_free_acc": acc(free), "mem_free_nomem_baseline": base,
        "mem_free_delta_vs_nomem": acc(free) - base,
        "avg_stored_memories": st.mean(r["n_memories"] for r in rv),
        "n": len(rv),
        "task_avg": (acc(use) + acc(free)) / 2,
        "overall_avg": acc(rv),
    }
print(f"{'metric':28s}{'add_only':>12s}{'add_delete':>12s}")
keys = list(rows["add_only"].keys())
for k in keys:
    a, d = rows["add_only"][k], rows["add_delete"][k]
    f = (lambda x: f"{x:12.1f}") if k not in ("n",) else (lambda x: f"{x:12d}")
    print(f"{k:28s}{f(a)}{f(d)}")
