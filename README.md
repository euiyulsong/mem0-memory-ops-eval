# mem0 메모리 연산 비교: add-only vs add+delete (합성 평가셋 100문항)

## 구성
- `data/dataset.jsonl`: 평가셋 100개 (메모리 사용 50, 메모리 미사용 50, 정정/변경 포함 33). 한국어 대화 세션 + 질문 + 정답 기준. gpt-6-luna로 생성한 합성 데이터.
- `data/results_run2.jsonl`: 추출 로그(`ingest_log`: 세션별 추출 fact, ADD/UPDATE/DELETE 결정 포함) 및 채점 결과.
- `scripts/gen_dataset.py`: 데이터셋 생성.
- `scripts/run_eval.py`: 두 방식 실행 및 채점. add-only는 mem0 `Memory.add()`, add+delete는 이전 mem0 ADD/UPDATE/DELETE 흐름을 패키지 프롬프트로 재구현.
- `scripts/summary.py`: 지표 집계.

## 방식 설명
- add-only: mem0 V3 ADDITIVE 추출 (ADD만 수행, 기존 기억 유지).
- add+delete: FACT_RETRIEVAL_PROMPT로 fact 추출 → 유사 기억 검색 → get_update_memory_messages로 ADD/UPDATE/DELETE/NONE 결정 → 적용.

## 결과 주의사항
- 결과는 실행마다 달라집니다. 같은 설정으로 두 번 돌렸을 때 메모리 미사용 태스크 점수가 add-only 96→100, add+delete 100→94로 바뀌었습니다. 두 방식 사이 차이는 노이즈 범위 안에 있습니다.
- 채점은 같은 LLM(gpt-6-luna)이 정답 기준과 비교하는 방식이라 자기 채점 편향이 있습니다.
- 생성과 실행 모두 OpenAI API를 사용합니다. 실행하려면 `OPENAI_API_KEY`와 mem0ai 패키지가 필요합니다.

## 재현
    pip install mem0ai
    python scripts/run_eval.py   # data/results.jsonl 생성
    python scripts/summary.py
