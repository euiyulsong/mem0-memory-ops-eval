"""LongMemEval(oracle, MIT)에서 100문항 평가셋을 만든다.

- mem_use 70: knowledge-update 35 (정보 갱신, has_update=True) + single-session-user 35
- mem_free 30: abstention(_abs) 전부 (대화에 답이 없는 질문)

입력: longmemeval_oracle.json  (https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned)
출력: data/dataset_longmemeval.jsonl
"""
import json, random, sys

src, dst = sys.argv[1], sys.argv[2]
D = json.load(open(src, encoding="utf-8"))
rng = random.Random(0)
ku = [d for d in D if d["question_type"] == "knowledge-update"]
su = [d for d in D if d["question_type"] == "single-session-user"]
ab = [d for d in D if d["question_id"].endswith("_abs")]
sel = [("mem_use", d, True) for d in rng.sample(ku, 35)] \
    + [("mem_use", d, False) for d in rng.sample(su, 35)] \
    + [("mem_free", d, False) for d in ab]

def sessions_of(d):
    # 사용자 발화만 세션별로 사용 (다른 데이터셋 실험과 동일)
    out = []
    for s in d["haystack_sessions"]:
        msgs = [t["content"] for t in s if t["role"] == "user"]
        if msgs: out.append(msgs)
    return out

with open(dst, "w", encoding="utf-8") as f:
    for t, d, upd in sel:
        it = {"id": f"{t}_{d['question_id']}", "type": t, "sessions": sessions_of(d),
              "query": d["question"], "gold": d["answer"], "has_update": upd,
              "source": "LongMemEval (oracle, MIT)", "source_question_type": d["question_type"]}
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
