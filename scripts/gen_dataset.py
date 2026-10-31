import os
import json, random, concurrent.futures as cf
from openai import OpenAI
client = OpenAI()
MODEL = "gpt-6-luna"

COMMON = """출력은 JSON {"items": [...]} 형식만. 각 item 필드:
- "sessions": 대화 세션 2~3개의 배열. 각 세션은 사용자 메시지 1~3개(문자열)의 배열. 한국어, 자연스러운 구어체.
- "query": 세션 이후에 사용자가 던지는 질문/요청 (한 문장).
- "gold": 정답 또는 채점 기준 (짧게, 핵심 키워드 포함).
- "has_update": 세션 중 앞서 말한 사실이 뒤에서 바뀌거나 정정되는 경우 true, 아니면 false.
서로 다른 주제/인물을 사용하고 중복을 피하세요."""

MEM_USE = """사용자의 개인 정보(이름, 직업, 거주지, 식습관, 반려동물, 취미, 일정, 가족, 선호 등)가 세션에 드러나고,
query는 **반드시 세션에 나온 개인 사실이 있어야만** 답할 수 있는 질문이어야 합니다. 
has_update가 true인 항목은 세션 후반에 앞선 사실을 정정/변경하는 내용이 들어가고, gold는 변경 후 최신 상태여야 합니다.
주제 힌트: {hint}
{n}개 생성."""

MEM_FREE = """세션에는 사용자의 개인 정보(취미, 직업, 반려동물, 식습관 등)가 들어 있지만,
query는 **개인 정보와 무관한 일반 지식/기술/상식 질문**이어야 합니다 (예: 코딩, 요리법, 과학 상식, 번역, 역사 등).
즉 개인 기억 없이도 정확히 답할 수 있어야 하며, 세션의 개인 정보를 쓰면 오히려 답이 어색해지는 질문이 좋습니다. has_update는 false.
주제 힌트: {hint}
{n}개 생성."""

HINTS_USE = ["거주지 이사", "직장 이직", "식습관/알레르기", "반려동물", "가족 구성", "여행 계획", "취미 변경", "운동 루틴", "휴대폰/기기", "학교/전공", "약속 일정", "음악 취향"]
HINTS_FREE = ["Python 코딩", "SQL 쿼리", "요리 레시피", "수학 개념", "역사 상식", "번역", "과학 상식", "영어 문법", "리눅스 명령어", "건강 일반 상식", "여행 일반 상식", "문서 작성 요령"]

def call(prompt):
    r = client.chat.completions.create(model=MODEL, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt + "\n\n" + COMMON}])
    return json.loads(r.choices[0].message.content)["items"]

jobs = []
for i in range(4):
    jobs.append(("mem_use", MEM_USE.format(hint=", ".join(random.Random(i).sample(HINTS_USE, 6)), n=13)))
for i in range(4):
    jobs.append(("mem_free", MEM_FREE.format(hint=", ".join(random.Random(10+i).sample(HINTS_FREE, 6)), n=13)))

out = {"mem_use": [], "mem_free": []}
with cf.ThreadPoolExecutor(8) as ex:
    futs = {ex.submit(call, p): t for t, p in jobs}
    for f in cf.as_completed(futs):
        try: out[futs[f]].extend(f.result())
        except Exception as e: print("gen error", e)

items = []
for t in ["mem_use", "mem_free"]:
    sel = out[t][:50]
    for i, it in enumerate(sel):
        items.append({"id": f"{t}_{i:02d}", "type": t, "sessions": it["sessions"], "query": it["query"],
                      "gold": it["gold"], "has_update": bool(it.get("has_update", False)) and t == "mem_use"})
print({t: sum(1 for x in items if x["type"] == t) for t in out}, "has_update:", sum(x["has_update"] for x in items))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "dataset.jsonl"), "w", encoding="utf-8") as f:
    for x in items: f.write(json.dumps(x, ensure_ascii=False) + "\n")
