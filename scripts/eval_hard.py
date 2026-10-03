"""
Hard retrieval evaluation for ASEEL.
 
eval_hit_at_5.py showed the retriever is robust to rewording (Hit@5 ~ 99.7%),
which is a ceiling. This script uses queries that can actually break a purely
deterministic search, and measures three things:
 
1. TYPO         the question with misspelled / alternately transliterated terms
                (Mafalet -> Mafalat, Al-Madbasa -> Al Madbasah)
2. DESCRIPTIVE  the question rewritten WITHOUT its proper names, describing the
                thing instead ("a dough dish eaten in Jazan")
3. FABRICATED   questions about invented terms that are NOT in the knowledge
                base. The only correct behaviour is to abstain.
 
Strategies (all use the real search tool, region filter included):
 
    pass1           one deterministic search
    gated_planner   pass1, plus the LLM planner only when confidence < 0.50
                    (the current system)
    always_planner  pass1 plus the LLM planner on every query
                    (shows what the planner is worth if the gate never blocked it)
 
Hit rules:
    strict   the SOURCE record's question appears in the top 5
    lenient  strict, OR an LLM judge says a top-5 record states the answer fact
             (the judge only runs on strict misses; --no-judge disables it)
Descriptive queries often match a different record that holds the same fact,
so strict alone underestimates them; report both.
 
The second question is the one that matters for the confidence gate: a table
shows, per top-1 relevance threshold, how many CORRECT, WRONG and FABRICATED
queries would pass. If wrong and fabricated queries pass as easily as correct
ones, relevance alone cannot be the gate.
 
Optional --pipeline-n N also runs N fabricated questions through the full
workflow (ask) and checks whether the final answer abstains.
 
Run:  python -m scripts.eval_hard --n 150
Queries are cached in data/eval/ so reruns are cheap and identical.
"""
 
from __future__ import annotations
 
import argparse
import csv
import random
import re
import time
from collections import defaultdict
from pathlib import Path
 
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
 
from agents.retrieval_agent import MAX_RESULTS, _merge, _search, plan_queries
from config.settings import OPENAI_MODEL_TOOL
 
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
EVAL_DIR = BASE_DIR / "data" / "eval"
 
REGION_MAP = {
    "CENTERAL.csv": "Central",
    "EAST.csv": "East",
    "NORTH.csv": "North",
    "SOUTH.csv": "South",
    "WEST.csv": "West",
    "GENERAL.csv": "General",
}
REGIONS = ["Central", "East", "North", "South", "West", "General"]
 
ARABIC = re.compile(r"[\u0600-\u06FF]")
GATE = 0.50  # same threshold route_after_validation uses
STRATEGIES = ["pass1", "gated_planner", "always_planner"]
VARIANTS = ["typo", "descriptive"]
THRESHOLDS = [0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
 
 
def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()
 
 
def _llm(schema):
    return ChatOpenAI(model=OPENAI_MODEL_TOOL, temperature=0).with_structured_output(
        schema
    )
 
 
def _invoke(llm, system: str, human: str, label: str):
    for attempt in range(3):
        try:
            return llm.invoke([("system", system), ("human", human)])
        except Exception as exc:
            print(f"  {label} failed (attempt {attempt + 1}): {exc!r}")
            time.sleep(2)
 
    return None
 
 
# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
 
def load_questions() -> tuple[list[dict], str]:
    """Unique (region, question) records with answers, plus the whole KB text."""
    found: dict[tuple[str, str], dict] = {}
    kb_parts: list[str] = []
 
    for file_name, region in REGION_MAP.items():
        path = RAW_DATA_DIR / file_name
 
        if not path.exists():
            print(f"Missing file: {file_name}")
            continue
 
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                row = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
                question = row.get("question", "").strip()
 
                if not question:
                    continue
 
                choices = row.get("choices", "").strip()
                answer = row.get("answer", "").strip()
                kb_parts.append(f"{question} {choices} {answer}")
 
                key = (region, norm(question))
                is_open = choices in ("", "–", "-")
                current = found.get(key)
 
                # Prefer the open-ended row: its answer is a full sentence.
                if current is None or (is_open and not current["is_open"]):
                    found[key] = {
                        "region": region,
                        "question": question,
                        "answer": answer,
                        "choices": choices,
                        "is_open": is_open,
                    }
 
    return list(found.values()), norm(" ".join(kb_parts))
 
 
def sample_questions(questions: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_region: dict[str, list[dict]] = defaultdict(list)
 
    for item in questions:
        by_region[item["region"]].append(item)
 
    total = len(questions)
    chosen: list[dict] = []
 
    for region in sorted(by_region):
        group = sorted(by_region[region], key=lambda q: q["question"])
        k = max(1, round(n * len(group) / total))
        chosen.extend(rng.sample(group, min(k, len(group))))
 
    return chosen
 
 
# --------------------------------------------------------------------------
# Query generation (cached)
# --------------------------------------------------------------------------
 
class VarItem(BaseModel):
    id: int
    typo: str
    descriptive: str
 
 
class VarBatch(BaseModel):
    items: list[VarItem]
 
 
VARIANT_PROMPT = """
You create HARD test queries for a Saudi cultural-knowledge search system.
You receive numbered questions. For EACH one return two rewrites:
 
- typo: the same question, but with realistic spelling trouble on the
  distinctive transliterated term(s) (for example Al-Madbasa -> Al Madbasah,
  Mafalet -> Mafalat, Qal'at -> Qalaa) and, optionally, one ordinary English
  typo. Keep every other word. If the question contains no transliterated
  term, return it unchanged.
- descriptive: the same question rewritten WITHOUT any of its proper names or
  distinctive terms, describing the thing by what it is, what it is made of,
  what it does or where it is, so that someone who does not know the name
  could still ask it. Keep a city or region if the question names one. If the
  question has no name or term to remove, return it unchanged.
 
Rules:
- Do NOT answer the question and do NOT add facts that are not in it.
- Write everything in English with Latin letters only (no Arabic script).
- Return one item per question, using the same id.
"""
 
 
def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
 
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))
 
 
def _write_rows(path: Path, fieldnames: list[str], rows: list[list]) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
 
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(fieldnames)
        writer.writerows(rows)
 
 
def load_variant_cache() -> dict[tuple[str, str, str], str]:
    cache = {}
 
    for row in _read_rows(EVAL_DIR / "hard_queries.csv"):
        if ARABIC.search(row["query"]):
            continue
        cache[(row["region"], row["gold_question"], row["variant"])] = row["query"]
 
    return cache
 
 
def save_variant_cache(cache: dict) -> None:
    _write_rows(
        EVAL_DIR / "hard_queries.csv",
        ["region", "gold_question", "variant", "query"],
        [[r, g, v, q] for (r, g, v), q in sorted(cache.items())],
    )
 
 
def generate_variants(sample: list[dict], cache: dict, batch_size: int) -> None:
    llm = _llm(VarBatch)
 
    for round_number in range(2):
        missing = [
            q
            for q in sample
            if any((q["region"], q["question"], v) not in cache for v in VARIANTS)
        ]
 
        if not missing:
            return
 
        print(f"Generating hard queries for {len(missing)} questions (round {round_number + 1})...")
 
        for start in range(0, len(missing), batch_size):
            chunk = missing[start : start + batch_size]
            numbered = "\n".join(f"{i}. {q['question']}" for i, q in enumerate(chunk))
            batch = _invoke(llm, VARIANT_PROMPT, numbered, "variant batch")
 
            if batch is None:
                continue
 
            for item in batch.items:
                if not 0 <= item.id < len(chunk):
                    continue
 
                q = chunk[item.id]
 
                for variant, text in (("typo", item.typo), ("descriptive", item.descriptive)):
                    text = (text or "").strip()
 
                    if ARABIC.search(text):
                        continue  # rejected; retried next round
 
                    # "" marks "nothing to change", so the item is skipped
                    # without being regenerated forever.
                    same = norm(text) == norm(q["question"])
                    cache[(q["region"], q["question"], variant)] = "" if same or not text else text
 
            save_variant_cache(cache)
            print(f"  {min(start + batch_size, len(missing))}/{len(missing)}")
 
 
class FakeItem(BaseModel):
    region: str
    term: str
    question: str
 
 
class FakeBatch(BaseModel):
    items: list[FakeItem]
 
 
FAKE_PROMPT = """
Invent NONEXISTENT Saudi cultural terms (a dish, drink, garment, craft, dance,
festival, game, place or custom) that sound like transliterated Arabic but are
not real. For each, write one natural English question about it, in the style
of "What is X?", "How is X prepared in <region>?" or "What is X traditionally
used for in <region>?".
 
Return exactly {n} items, spread evenly across these regions: Central, East,
North, South, West, General (use "General" for nationwide questions).
Each item has: region, term (only the invented term), question.
Write in English with Latin letters only.
"""
 
 
def load_fabricated(kb_text: str, count: int) -> list[dict]:
    path = EVAL_DIR / "hard_fabricated.csv"
    rows = _read_rows(path)
 
    if len(rows) >= count:
        return rows[:count]
 
    print(f"Generating {count} fabricated questions...")
    batch = _invoke(_llm(FakeBatch), FAKE_PROMPT.format(n=count), "Generate them.", "fabricated batch")
    items: list[dict] = []
    seen: set[str] = set()
 
    for item in (batch.items if batch else []):
        term = norm(item.term)
 
        # The term must be absent from the knowledge base, otherwise the
        # correct behaviour is not "abstain".
        if (
            item.region in REGIONS
            and term
            and term not in seen
            and term not in kb_text
            and not ARABIC.search(item.question)
        ):
            seen.add(term)
            items.append({"region": item.region, "term": item.term, "question": item.question})
 
    _write_rows(path, ["region", "term", "question"], [[i["region"], i["term"], i["question"]] for i in items])
    print(f"  kept {len(items)} terms that are absent from the knowledge base")
    return items
 
 
# --------------------------------------------------------------------------
# Retrieval strategies and judging
# --------------------------------------------------------------------------
 
def confidence(records: list[dict], region: str) -> float:
    try:
        from tools.evidence_validation import validate_evidence
 
        _, _, score = validate_evidence(records, region or None)
        return float(score)
    except Exception:
        return max((r.get("relevance") or 0 for r in records), default=0.0)
 
 
def top1(records: list[dict]) -> float:
    return float(records[0].get("relevance") or 0) if records else 0.0
 
 
def run_strategies(query: str, region: str, use_planner: bool) -> dict:
    first = _merge([_search(query, region)])[:MAX_RESULTS]
    conf = confidence(first, region)
 
    planned: list[str] = []
    extended = first
 
    if use_planner:
        planned = plan_queries(
            {
                "query": query,
                "retrieval_query": query,
                "region": region,
                "category": None,
                "validation_reason": "low relevance",
                "retrieved": first,
                "raw_semantic_results": first,
            }
        )
        extended = _merge([first] + [_search(p, region) for p in planned])[:MAX_RESULTS]
 
    return {
        "results": {
            "pass1": first,
            "gated_planner": extended if conf < GATE else first,
            "always_planner": extended,
        },
        "confidence": conf,
        "planned": planned,
    }
 
 
def rank_of(gold: str, records: list[dict]) -> int | None:
    target = norm(gold)
 
    for position, record in enumerate(records[:MAX_RESULTS], start=1):
        if norm(record.get("question", "")) == target:
            return position
 
    return None
 
 
class Verdict(BaseModel):
    rank: int
 
 
JUDGE_PROMPT = """
You judge a retrieval system. You get a user query, the reference question and
answer it was derived from, and up to 5 retrieved records.
 
Return the 1-based rank of the FIRST record that actually states the fact needed
to answer the reference question. A record that only shares the topic does NOT
count. Return 0 if no record states that fact.
"""
 
 
class Judge:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.llm = _llm(Verdict) if enabled else None
        self.cache: dict[tuple, int | None] = {}
 
    def rank(self, query: str, source: dict, records: list[dict]) -> int | None:
        if not self.enabled or not records:
            return None
 
        key = (norm(query), tuple(norm(r.get("question", "")) for r in records))
 
        if key in self.cache:
            return self.cache[key]
 
        listing = "\n".join(
            f"{i}. Q: {r.get('question', '')}\n   A: {r.get('answer', '')}"
            for i, r in enumerate(records, start=1)
        )
        human = (
            f"User query: {query}\n"
            f"Reference question: {source['question']}\n"
            f"Reference choices: {source['choices'] or 'none'}\n"
            f"Reference answer: {source['answer']}\n\n"
            f"Retrieved records:\n{listing}"
        )
        verdict = _invoke(self.llm, JUDGE_PROMPT, human, "judge")
        rank = verdict.rank if verdict and 1 <= verdict.rank <= len(records) else None
        self.cache[key] = rank
        return rank
 
 
# --------------------------------------------------------------------------
# Optional: full-pipeline abstention test
# --------------------------------------------------------------------------
 
class Abstain(BaseModel):
    abstains: bool
 
 
ABSTAIN_PROMPT = """
A user asked about a term that does NOT exist in the knowledge base. Does the
answer abstain, meaning it says it lacks reliable information or cannot answer,
rather than describing the term as if it were real?
abstains = true: declines, or says it has no information (even if it adds
generic context). abstains = false: it states facts about the term.
"""
 
 
def pipeline_abstention(fabricated: list[dict], n: int) -> None:
    from workflow.graph import ask
 
    judge = _llm(Abstain)
    sample = random.Random(7).sample(fabricated, min(n, len(fabricated)))
    abstained = 0
    invented: list[tuple[dict, str]] = []
 
    print(f"\nRunning {len(sample)} fabricated questions through the full pipeline...")
 
    for index, item in enumerate(sample, start=1):
        try:
            result = ask(item["question"], region_override=item["region"])
            answer = (result.get("answer") or "").strip()
        except Exception as exc:
            print(f"  ask failed: {exc!r}")
            continue
 
        verdict = _invoke(
            judge,
            ABSTAIN_PROMPT,
            f"Question: {item['question']}\n\nAnswer: {answer}",
            "abstain judge",
        )
 
        if verdict and verdict.abstains:
            abstained += 1
        else:
            invented.append((item, answer))
 
        if index % 10 == 0:
            print(f"  {index}/{len(sample)}")
 
    done = abstained + len(invented)
 
    print("\n" + "=" * 66)
    print("FULL PIPELINE: FABRICATED QUESTIONS")
    print("=" * 66)
    print(f"Abstained correctly: {abstained}/{done} ({abstained / max(done, 1):.1%})")
    print(f"Answered as if real: {len(invented)}/{done}")
 
    for item, answer in invented[:8]:
        print(f"\n  [{item['region']}] {item['question']}")
        print(f"      answer: {answer[:180]}")
 
 
# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
 
def summarize(ranks: list[int | None]) -> dict:
    n = len(ranks)
 
    if not n:
        return {"n": 0, "hit1": 0.0, "hit5": 0.0, "mrr": 0.0}
 
    return {
        "n": n,
        "hit1": sum(1 for r in ranks if r == 1) / n,
        "hit5": sum(1 for r in ranks if r is not None) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
    }
 
 
def print_variant_table(title: str, rows: list[dict]) -> None:
    print("\n" + "=" * 78)
    print(f"{title}  (N={len(rows)})")
    print("=" * 78)
    print(f"{'strategy':<16}{'strict@1':>10}{'strict@5':>10}{'lenient@1':>11}{'lenient@5':>11}{'MRR(len)':>10}")
 
    for strategy in STRATEGIES:
        strict = summarize([r[f"strict_{strategy}"] for r in rows])
        lenient = summarize([r[f"lenient_{strategy}"] for r in rows])
        print(
            f"{strategy:<16}{strict['hit1']:>10.1%}{strict['hit5']:>10.1%}"
            f"{lenient['hit1']:>11.1%}{lenient['hit5']:>11.1%}{lenient['mrr']:>10.3f}"
        )
 
 
def print_gate_table(rows: list[dict], fab_rows: list[dict]) -> None:
    correct = [r for r in rows if r["lenient_pass1"] is not None]
    wrong = [r for r in rows if r["lenient_pass1"] is None]
 
    print("\n" + "=" * 78)
    print("CAN RELEVANCE ALONE BE THE GATE?  (share of queries whose top-1 passes)")
    print("=" * 78)
    print(f"correct = answer found ({len(correct)}), wrong = answer not found "
          f"({len(wrong)}), fabricated = absent from KB ({len(fab_rows)})")
    print(f"{'top-1 >=':<10}{'correct':>10}{'wrong':>10}{'fabricated':>13}")
 
    for t in THRESHOLDS:
        def share(group):
            return sum(1 for r in group if r["top1"] >= t) / len(group) if group else 0.0
 
        print(f"{t:<10.2f}{share(correct):>10.1%}{share(wrong):>10.1%}{share(fab_rows):>13.1%}")
 
    gate_fab = sum(1 for r in fab_rows if r["confidence"] >= GATE)
    gate_wrong = sum(1 for r in wrong if r["confidence"] >= GATE)
    print(
        f"\nActual gate (validate_evidence >= {GATE}): fabricated pass "
        f"{gate_fab}/{len(fab_rows)}, wrong-evidence pass {gate_wrong}/{len(wrong)}"
    )
 
 
def show(title: str, rows: list[dict], line, limit: int = 8) -> None:
    print(f"\n{title} ({len(rows)})")
 
    for row in rows[:limit]:
        print(line(row))
 
 
# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
 
def main() -> None:
    parser = argparse.ArgumentParser(description="Hard retrieval evaluation.")
    parser.add_argument("--n", type=int, default=150, help="questions to sample")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--fake", type=int, default=60, help="fabricated questions")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--no-planner", action="store_true")
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--pipeline-n", type=int, default=0, help="also run N fabricated questions through ask()")
    args = parser.parse_args()
 
    questions, kb_text = load_questions()
    sample = sample_questions(questions, args.n, args.seed)
    print(f"Loaded {len(questions)} unique questions; sampled {len(sample)} (seed={args.seed})")
 
    cache = load_variant_cache()
    generate_variants(sample, cache, args.batch_size)
    fabricated = load_fabricated(kb_text, args.fake)
 
    judge = Judge(enabled=not args.no_judge)
    use_planner = not args.no_planner
 
    jobs = [
        (q, v)
        for q in sample
        for v in VARIANTS
        if cache.get((q["region"], q["question"], v))
    ]
    print(f"Evaluating {len(jobs)} hard queries (+{len(fabricated)} fabricated)...")
 
    rows: list[dict] = []
 
    for index, (q, variant) in enumerate(jobs, start=1):
        region = q["region"]
        query = cache[(region, q["question"], variant)]
        out = run_strategies(query, region, use_planner)
 
        row = {
            "region": region,
            "variant": variant,
            "gold_question": q["question"],
            "query": query,
            "top1": top1(out["results"]["pass1"]),
            "confidence": out["confidence"],
            "planned": " | ".join(out["planned"]),
        }
 
        for strategy in STRATEGIES:
            records = out["results"][strategy]
            strict = rank_of(q["question"], records)
            row[f"strict_{strategy}"] = strict
            row[f"lenient_{strategy}"] = strict or judge.rank(query, q, records)
 
        rows.append(row)
 
        if index % 25 == 0:
            print(f"  {index}/{len(jobs)}")
 
    fab_rows = []
 
    for item in fabricated:
        out = run_strategies(item["question"], item["region"], False)
        records = out["results"]["pass1"]
        fab_rows.append(
            {
                "region": item["region"],
                "query": item["question"],
                "top1": top1(records),
                "confidence": out["confidence"],
                "best": records[0].get("question", "") if records else "",
            }
        )
 
    if not rows:
        print("No hard queries were generated.")
        return
 
    # ---- save
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_file = EVAL_DIR / "hard_results.csv"
 
    with out_file.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
 
    # ---- report
    print_variant_table("ALL HARD QUERIES", rows)
 
    for variant in VARIANTS:
        print_variant_table(f"VARIANT: {variant}", [r for r in rows if r["variant"] == variant])
 
    print_gate_table(rows, fab_rows)
 
    gated_used = sum(1 for r in rows if r["confidence"] < GATE and r["planned"])
    print(f"\nPlanner reached by the gate on {gated_used}/{len(rows)} queries; "
          f"always_planner ran on {sum(1 for r in rows if r['planned'])}")
 
    show(
        "RESCUED BY ALWAYS-PLANNER (pass1 missed, always_planner found it)",
        [r for r in rows if r["lenient_pass1"] is None and r["lenient_always_planner"] is not None],
        lambda r: f"  [{r['region']}/{r['variant']}] {r['query']}\n      planned: {r['planned']}",
    )
    show(
        "HURT BY ALWAYS-PLANNER (pass1 found it, always_planner lost it)",
        [r for r in rows if r["lenient_pass1"] is not None and r["lenient_always_planner"] is None],
        lambda r: f"  [{r['region']}/{r['variant']}] {r['query']}\n      planned: {r['planned']}",
    )
    show(
        "STILL MISSED by every strategy",
        [r for r in rows if all(r[f"lenient_{s}"] is None for s in STRATEGIES)],
        lambda r: f"  [{r['region']}/{r['variant']}] {r['query']}\n      source: {r['gold_question']}",
    )
    show(
        "DANGEROUS: fabricated questions that PASS the gate",
        [r for r in fab_rows if r["confidence"] >= GATE],
        lambda r: f"  [{r['region']}] {r['query']}\n      conf={r['confidence']:.2f}, matched: {r['best']}",
    )
 
    print(f"\nSaved per-query results to:\n{out_file}")
 
    if args.pipeline_n:
        pipeline_abstention(fabricated, args.pipeline_n)
 
 
if __name__ == "__main__":
    main()