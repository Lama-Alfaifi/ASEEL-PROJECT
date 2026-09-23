from retrieval.ingestion import _resolve_mcq_answer

# NORTH.csv row that caused the DeepEval faithfulness failure
answer1 = _resolve_mcq_answer(
    "A",
    "A. Al-Sidriyah and Thobe B. Al-Marodn C. Al-Dishdashah D. Al-Mufrij",
)
print(repr(answer1))

# EAST.csv-style answer — must stay unchanged (idempotent check)
answer2 = _resolve_mcq_answer(
    "C. Al-Dishdasha",
    "A. Al-Mirwaden B. Al-Thobe and Al-Sudairi C. Al-Dishdasha D. Al-Mufraj",
)
print(repr(answer2))
