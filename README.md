# mem0 메모리 연산 비교: add-only vs add+delete (합성 평가셋 100문항)

이전 mem0 방식(ADD/UPDATE/DELETE)과 add-only(ADD만) 방식을 같은 평가셋으로 비교합니다.

## 방식
- **add-only**: mem0 V3 ADDITIVE 추출. ADD만 수행하고 기존 기억은 건드리지 않습니다.
- **add+delete**: FACT_RETRIEVAL_PROMPT로 fact 추출 → 유사 기억 검색 → `get_update_memory_messages`로 ADD/UPDATE/DELETE/NONE 결정 → 적용. 패키지 프롬프트로 재구현했으며 구버전 릴리스 그대로는 아닙니다.

## 데이터 예시
메모리 사용 태스크 (`mem_use_00`, 정정 포함):
```json
{
  "id": "mem_use_00",
  "type": "mem_use",
  "sessions": [
    [
      "강아지 한 마리 키우는데 이름은 보리야. 네 살 된 말티즈야.",
      "요즘 보리랑 저녁마다 동네 공원 산책해."
    ],
    [
      "아까 강아지 이름 잘못 말했어. 보리가 아니라 두부야. 네 살 말티즈인 건 맞아."
    ]
  ],
  "query": "내 강아지 이름이랑 견종이 뭐였지?",
  "gold": "두부, 말티즈",
  "has_update": true
}
```

메모리 미사용 태스크 (`mem_free_02`, 개인 정보와 무관한 질문):
```json
{
  "id": "mem_free_02",
  "type": "mem_free",
  "sessions": [
    [
      "다음 달에 동호회에서 작은 전시회를 열기로 했어."
    ],
    [
      "나는 안내문 문구를 맡았어.",
      "너무 딱딱하지 않게 쓰고 싶어."
    ]
  ],
  "query": "문서의 핵심 내용을 짧게 전달하는 요약문을 쓸 때 유용한 원칙은 무엇인가요?",
  "gold": "핵심 목적과 결론을 먼저 제시하고, 중요한 근거만 간결하게 남기며, 불필요한 세부사항은 덜어낸다.",
  "has_update": false
}
```

## 추출 로그 예시 (`mem_use_00`)
add-only 추출 결과:
```json
[
  {
    "session": 0,
    "extracted_facts": [
      "사용자는 보리라는 이름의 네 살 된 말티즈를 키우며, 2026년 10월 말 요즘 보리와 저녁마다 동네 공원을 산책하고 있다."
    ],
    "actions": [
      {
        "event": "ADD",
        "text": "사용자는 보리라는 이름의 네 살 된 말티즈를 키우며, 2026년 10월 말 요즘 보리와 저녁마다 동네 공원을 산책하고 있다."
      }
    ]
  },
  {
    "session": 1,
    "extracted_facts": [
      "사용자가 앞서 잘못 말한 강아지 이름을 보리에서 두부로 정정했다. 두부는 네 살 된 말티즈다."
    ],
    "actions": [
      {
        "event": "ADD",
        "text": "사용자가 앞서 잘못 말한 강아지 이름을 보리에서 두부로 정정했다. 두부는 네 살 된 말티즈다."
      }
    ]
  }
]
```
add+delete 추출 결과:
```json
[
  {
    "session": 0,
    "extracted_facts": [
      "강아지 한 마리를 키우며, 이름은 보리이다.",
      "보리는 네 살 된 말티즈이다.",
      "요즘 저녁마다 보리와 동네 공원을 산책한다."
    ],
    "actions": [
      {
        "id": "0",
        "text": "강아지 한 마리를 키우며, 이름은 보리이다.",
        "event": "ADD"
      },
      {
        "id": "1",
        "text": "보리는 네 살 된 말티즈이다.",
        "event": "ADD"
      },
      {
        "id": "2",
        "text": "요즘 저녁마다 보리와 동네 공원을 산책한다.",
        "event": "ADD"
      }
    ]
  },
  {
    "session": 1,
    "extracted_facts": [
      "강아지 이름은 두부이다",
      "두부는 네 살 말티즈이다"
    ],
    "actions": [
      {
        "id": "0",
        "text": "강아지 한 마리를 키우며, 이름은 두부이다.",
        "event": "UPDATE",
        "old_memory": "강아지 한 마리를 키우며, 이름은 보리이다."
      },
      {
        "id": "1",
        "text": "두부는 네 살 된 말티즈이다.",
        "event": "UPDATE",
        "old_memory": "보리는 네 살 된 말티즈이다."
      },
      {
        "id": "2",
        "text": "요즘 저녁마다 두부와 동네 공원을 산책한다.",
        "event": "UPDATE",
        "old_memory": "요즘 저녁마다 보리와 동네 공원을 산책한다."
      }
    ]
  }
]
```
두 방식 모두 정정 세션에서 "두부"를 최신 값으로 답했습니다. 차이는 저장 구조입니다. add+delete는 옛 기억을 UPDATE하고, add-only는 옛 기억을 두고 새 기억을 추가합니다.

## 결과
같은 평가셋을 두 번 돌린 결과입니다. 점수가 실행마다 달라졌기 때문에 두 번 다 적습니다.

| 지표 | add-only (1차) | add+delete (1차) | add-only (2차) | add+delete (2차) |
|---|---|---|---|---|
| 메모리 사용 정확도 (50) | 98.0 | 100.0 | 98.0 | 98.0 |
| └ 정정 포함 (33) | 97.0 | 100.0 | 100.0 | 100.0 |
| └ 정정 없음 (17) | 100.0 | 100.0 | 94.1 | 94.1 |
| 메모리 미사용 정확도 (50) | 96.0 | 96.0 | 100.0 | 94.0 |
| └ 기억 없이 답했을 때 (기준선) | 94.0 | 100.0 | 94.0 | 92.0 |
| 평균 저장 기억 수 | 2.2 | 2.5 | 2.2 | 2.5 |
| **태스크 평균 (사용+미사용)/2** | **97.0** | **98.0** | **99.0** | **96.0** |
| 전체 100문항 평균 | 97.0 | 98.0 | 99.0 | 96.0 |

### 해석
- 두 방식의 차이는 1~6점이고, 같은 설정에서도 점수가 바뀌었습니다. 두 방식 중 어느 쪽이 낫다고 결론 내리기 어렵습니다.
- 평균은 1차에서 add+delete가 1점 높았고, 2차에서는 add-only가 3점 높았습니다.
- 정정 케이스는 두 실행 모두 add+delete가 100이었지만, 2차에서는 add-only도 100이었습니다.
- 메모리 미사용 태스크의 기준선도 같은 질문인데 실행마다 달라졌습니다. 채점 노이즈가 최소 ±6점 수준이라는 뜻입니다.
- 저장 기억 수는 add-only가 적습니다 (2.2 vs 2.5).

## 한계
- 합성 데이터 100문항, 1회 실행 × 2번 기준입니다. 통계적 검정은 하지 않았습니다.
- 채점은 같은 LLM(gpt-6-luna)이 정답 기준과 비교하는 방식이라 자기 채점 편향이 있습니다.
- 실행 과정에서 OpenAI API를 사용합니다.

## 파일 (1·2차, 합성 데이터)
- `data/dataset.jsonl`: 평가셋 100개
- `data/results_run2.jsonl`: 2차 실행 결과 (추출 로그, 검색 기억, 답변, 채점 포함)
- `scripts/gen_dataset.py`: 데이터셋 생성
- `scripts/run_eval.py`: 두 방식 실행 및 채점
- `scripts/summary.py`: 지표 집계

## 재현
```
pip install mem0ai
python scripts/run_eval.py   # data/results.jsonl 생성
python scripts/summary.py
```

---

## 3차 실행: 공개 데이터셋 (LongMemEval)

합성 데이터 대신 [LongMemEval](https://github.com/xiaowu0162/LongMemEval) (MIT License, oracle split)로 다시 돌렸습니다. 원본은 `longmemeval_oracle.json`이고, 이 저장소에는 그중 100문항만 들어 있습니다.

### 구성
- 메모리 사용 70: knowledge-update 35 (정보 갱신, `has_update=true`) + single-session-user 35
- 메모리 미사용 30: abstention 문항 전부 (대화에 답이 없는 질문)

1·2차와 셋이 다르고 미사용 쪽의 정의도 다릅니다. 세 번의 점수를 직접 비교하면 안 됩니다.

### 결과

| 지표 | add-only | add+delete |
|---|---|---|
| 메모리 사용 정확도 (70) | 94.3 | 85.7 |
| └ 정보 갱신 (35) | 88.6 | 77.1 |
| └ 단일 세션 사용자 정보 (35) | 100.0 | 94.3 |
| 메모리 미사용 정확도 (30, abstention) | 76.7 | 80.0 |
| └ 기억 없이 답했을 때 | 73.3 | 76.7 |
| 평균 저장 기억 수 | 7.2 | 8.9 |
| **태스크 평균** | **85.5** | **82.9** |
| 전체 100문항 평균 | 89.0 | 84.0 |

### 해석
- 이번 셋에서는 add-only가 메모리 사용 쪽에서 앞섰습니다. 1차 합성 셋에서는 add+delete가 정정 케이스에서 앞섰으므로 방향이 반대입니다.
- 정보 갱신 35문항에서 3문항 차이가 8.6점입니다. 표본이 작아서 노이즈가 큽니다.
- 정답은 영어이고 답변 프롬프트는 한국어로 답하도록 되어 있습니다. 채점 모델이 교차 언어를 비교하므로 점수에 영향이 있을 수 있습니다.

### 파일
- `data/dataset_longmemeval.jsonl`: 3차 평가셋 100문항
- `data/results_run3_longmemeval.jsonl`: 3차 실행 결과
- `scripts/make_longmemeval_set.py`: LongMemEval에서 평가셋을 만드는 스크립트 (`python scripts/make_longmemeval_set.py longmemeval_oracle.json data/dataset_longmemeval.jsonl`)

### 출처
LongMemEval (Wu et al.), MIT License. https://github.com/xiaowu0162/LongMemEval
