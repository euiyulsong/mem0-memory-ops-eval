import os, json, uuid, time, concurrent.futures as cf
os.environ["MEM0_TELEMETRY"] = "false"
from mem0 import Memory
from mem0.configs.prompts import FACT_RETRIEVAL_PROMPT, get_update_memory_messages
from mem0.memory.utils import remove_code_blocks
from openai import OpenAI

BASE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE, "store")
client = OpenAI()
LLM = "gpt-6-luna"
TOPK = 5

def chat(messages, json_mode=False):
    kw = {"response_format": {"type": "json_object"}} if json_mode else {}
    for attempt in range(3):
        try:
            r = client.chat.completions.create(model=LLM, messages=messages, **kw)
            return r.choices[0].message.content or ""
        except Exception as e:
            err = e; time.sleep(2)
    raise err

def make_mem(variant, idx):
    cfg = {
        "llm": {"provider": "openai", "config": {"model": LLM}},
        "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small"}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": "mem", "path": os.path.join(STORE, f"{variant}_{idx}"),
            "on_disk": True, "embedding_model_dims": 1536}},
        "history_db_path": os.path.join(STORE, f"{variant}_{idx}", "history.db"),
    }
    return Memory.from_config(cfg)

def ingest_add_only(mem, uid, sessions):
    log = []
    for i, sess in enumerate(sessions):
        res = mem.add([{"role": "user", "content": m} for m in sess], user_id=uid, infer=True)["results"]
        log.append({"session": i, "extracted_facts": [r["memory"] for r in res], "actions": [{"event": r["event"], "text": r["memory"]} for r in res]})
    return log

def ingest_add_delete(mem, uid, sessions):
    # 이전 mem0 방식: fact 추출 -> 유사 기억 검색 -> ADD/UPDATE/DELETE 결정 -> 적용
    vs = mem.vector_store
    log = []
    for i, sess in enumerate(sessions):
        text = "\n".join(f"user: {m}" for m in sess)
        raw = chat([{"role": "system", "content": FACT_RETRIEVAL_PROMPT},
                    {"role": "user", "content": f"Input:\n{text}"}], json_mode=True)
        try: facts = json.loads(remove_code_blocks(raw)).get("facts", [])
        except Exception: facts = []
        if not facts:
            log.append({"session": i, "extracted_facts": [], "actions": []}); continue
        idmap, old = {}, []
        for f in facts:
            emb = mem.embedding_model.embed(f, "search")
            for h in vs.search(query=f, vectors=emb, top_k=TOPK, filters={"user_id": uid}):
                if h.id not in idmap.values():
                    k = str(len(idmap)); idmap[k] = h.id
                    old.append({"id": k, "text": h.payload.get("data", "")})
        prompt = get_update_memory_messages(old, json.dumps(facts, ensure_ascii=False))
        raw = chat([{"role": "user", "content": prompt}], json_mode=True)
        try: acts = json.loads(remove_code_blocks(raw)).get("memory", [])
        except Exception: acts = []
        log.append({"session": i, "extracted_facts": facts, "actions": acts})
        for a in acts:
            ev, t = a.get("event"), a.get("text", "")
            if ev == "ADD" and t:
                vs.insert(vectors=[mem.embedding_model.embed(t, "add")],
                          payloads=[{"data": t, "user_id": uid}], ids=[str(uuid.uuid4())])
            elif ev == "UPDATE" and idmap.get(a.get("id")):
                vs.update(vector_id=idmap[a["id"]], vector=mem.embedding_model.embed(t, "add"),
                          payload={"data": t, "user_id": uid})
            elif ev == "DELETE" and idmap.get(a.get("id")):
                vs.delete(vector_id=idmap[a["id"]])
    return log

def retrieve(mem, variant, uid, query):
    if variant == "add_only":
        res = mem.search(query=query, filters={"user_id": uid}, top_k=TOPK)["results"]
        return [r["memory"] for r in res]
    emb = mem.embedding_model.embed(query, "search")
    hits = mem.vector_store.search(query=query, vectors=emb, top_k=TOPK, filters={"user_id": uid})
    return [h.payload.get("data", "") for h in hits]

def answer(query, memories=None):
    if memories:
        ctx = "\n".join(f"- {m}" for m in memories)
        sys = f"다음은 사용자에 대해 기억하고 있는 정보입니다:\n{ctx}\n\n관련 정보가 있으면 반영해서, 질문에 한국어로 간결하게 답하세요."
    else:
        sys = "질문에 한국어로 간결하게 답하세요."
    return chat([{"role": "system", "content": sys}, {"role": "user", "content": query}])

JUDGE = """질문, 정답 기준, 모델 답변이 주어집니다. 답변이 정답 기준의 핵심 내용을 맞게 담고 있으면 1, 틀리거나 핵심이 빠지면 0.
JSON으로만 답하세요: {"correct": 0 또는 1}"""

def judge(query, gold, ans):
    raw = chat([{"role": "system", "content": JUDGE},
                {"role": "user", "content": f"질문: {query}\n정답 기준: {gold}\n모델 답변: {ans}"}], json_mode=True)
    try: return int(json.loads(raw).get("correct", 0))
    except Exception: return 0

def run_one(variant, idx, item):
    uid = f"{variant}_{item['id']}"
    mem = make_mem(variant, idx)
    if variant == "add_only": ilog = ingest_add_only(mem, uid, item["sessions"])
    else: ilog = ingest_add_delete(mem, uid, item["sessions"])
    n_mem = len(mem.get_all(filters={"user_id": uid})["results"]) if variant == "add_only" \
        else len(mem.vector_store.list(filters={"user_id": uid}, top_k=1000)[0])
    mems = retrieve(mem, variant, uid, item["query"])
    ans = answer(item["query"], mems)
    rec = {"variant": variant, "id": item["id"], "type": item["type"], "has_update": item["has_update"],
           "n_memories": n_mem, "ingest_log": ilog, "retrieved": mems, "answer": ans,
           "correct": judge(item["query"], item["gold"], ans)}
    if item["type"] == "mem_free":  # 기억 없이 답했을 때 기준선
        base = answer(item["query"], None)
        rec["baseline_answer"] = base
        rec["baseline_correct"] = judge(item["query"], item["gold"], base)
    return rec

if __name__ == "__main__":
    items = [json.loads(l) for l in open(os.path.join(BASE, "..", "data", "dataset.jsonl"), encoding="utf-8")]
    tasks = [(v, i, it) for v in ["add_only", "add_delete"] for i, it in enumerate(items)]
    out_path = os.path.join(BASE, "..", "data", "results.jsonl")
    results = []
    with cf.ThreadPoolExecutor(12) as ex:
        futs = {ex.submit(run_one, *t): t for t in tasks}
        for n, f in enumerate(cf.as_completed(futs), 1):
            v, i, it = futs[f]
            try: results.append(f.result())
            except Exception as e: print("FAIL", v, it["id"], repr(e)[:200])
            if n % 50 == 0: print("done", n, "/", len(tasks), flush=True)
    with open(out_path, "w", encoding="utf-8") as fo:
        for r in results: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("saved", len(results), "->", out_path)
