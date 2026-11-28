"""Run L01_T01: fixed trace, three-size verification, cost counts and timings."""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import timeit
from typing import Optional

from .catalogue import expand_catalogue, load_catalogue, save_catalogue
from .cost_models import MODEL_NOTES, parallel_filter_trace, simulate_block_reads
from .reference import reference_search
from .search import instrumented_search, linear_search

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIZES = (20, 1_000, 10_000)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def benchmark(products: list, samples: int = 9) -> dict:
    """Warm repeated batches; parsing, oracle and instrumentation are excluded."""
    for _ in range(5):
        linear_search(products)
    timer = timeit.Timer(lambda: linear_search(products))
    batch = 1
    while timer.timeit(number=batch) < 0.01 and batch < 1_048_576:
        batch *= 2
    raw = [timer.timeit(number=batch) * 1_000_000 / batch for _ in range(samples)]
    return {
        "unit": "microseconds per query",
        "samples": samples,
        "queries_per_sample": batch,
        "raw_sample_means_us": raw,
        "median_us": statistics.median(raw),
        "min_us": min(raw),
        "max_us": max(raw),
        "ns_per_record": statistics.median(raw) * 1000 / len(products),
    }


def run_session(output: Optional[Path] = None) -> dict:
    output = output or PROJECT_ROOT / "results" / "session01"
    fixture_path = PROJECT_ROOT / "data" / "products_20.json"
    expectation_path = PROJECT_ROOT / "data" / "session01_expected.json"
    fixture = load_catalogue(fixture_path)
    expectation = json.loads(expectation_path.read_text(encoding="utf-8"))
    if len(fixture) != 20:
        raise AssertionError("Session 1 requires the fixed 20-record fixture")
    manual_ids = expectation["expected_ids"]
    expected_membership = set(manual_ids)
    query = expectation["query"]
    if query != {"category": "laptop", "max_price": 60_000, "price_operator": "<", "stock_operator": "> 0"}:
        raise AssertionError("The frozen Session 1 query changed")

    cases = []
    comparisons = []
    for size in SIZES:
        # Serialize and reload each size so ingestion is exercised before search.
        products = expand_catalogue(fixture, size)
        generated_path = output / "catalogues" / f"products_{size}.json"
        save_catalogue(products, generated_path)
        products = load_catalogue(generated_path)
        # Lift the separately recorded manual decisions to each repeated fixture.
        expected = [p.id for index, p in enumerate(products) if fixture[index % 20].id in expected_membership]
        observed = linear_search(products)
        instrumented, counts = instrumented_search(products)
        oracle = reference_search(products)
        if not (expected == observed == instrumented == oracle):
            raise AssertionError(f"ID/order mismatch at n={size}")
        metrics = asdict(counts) | {
            "predicate_comparisons": counts.predicate_comparisons,
            "counted_operations": counts.counted_operations,
        }
        if metrics != {name: value * (size // 20) for name, value in expectation["counts"].items()}:
            raise AssertionError(f"Operation counts differ from the manual trace at n={size}")
        blocks = {str(block_size): simulate_block_reads(size, block_size) for block_size in (4, 16, 64)}
        timing = benchmark(products)
        cases.append({
            "size": size, "matches": len(observed), "correct": True,
            "counts": metrics, "simulated_input_block_reads": blocks,
            "ideal_predicate_rounds_p4": (size + 3) // 4,
            "timing": timing,
        })
        comparisons.append({
            "size": size, "expected_ids": expected, "observed_ids": observed,
            "sql_oracle_ids": oracle, "instrumented_matches": instrumented == observed,
            "all_equal_in_input_order": True,
        })

    trace = []
    for index, product in enumerate(fixture):
        category_ok = product.category == "laptop"
        stock_ok = product.stock > 0 if category_ok else None
        price_ok = product.price < 60_000 if stock_ok else None
        selected = bool(category_ok and stock_ok and price_ok)
        expected_decision = expectation["decisions"][index]
        if expected_decision["id"] != product.id or expected_decision["match"] != selected:
            raise AssertionError(f"Manual decision mismatch: {product.id}")
        trace.append({
            "record": index + 1, "id": product.id, "category": product.category,
            "price": product.price, "stock": product.stock,
            "category_pass": category_ok, "stock_pass": stock_ok,
            "price_pass": price_ok, "match": selected,
            "comparisons": 1 + int(category_ok) + int(bool(stock_ok)),
            "block_B4": index // 4,
            "new_block_read": index % 4 == 0,
            "manual_reason": expected_decision["reason"],
        })

    summary = {
        "artifact": "L01_T01",
        "query": query,
        "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "expected_sha256": hashlib.sha256(expectation_path.read_bytes()).hexdigest(),
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "os": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "logical_cpus": os.cpu_count(),
        },
        "protocol": {
            "data": "synthetic deterministic repetitions; identical attribute mix; unique IDs; 30% matches",
            "timed": "uninstrumented linear search, query validation and result allocation/destruction",
            "excluded": "loading, data generation, tracing, counters, block simulation and SQL oracle",
            "warmup": "five searches plus batch calibration; each batch targets at least 10 ms",
            "repeats": "nine batch means; report median and min/max; timeit disables cyclic GC during each batch",
            "limitations": "local warm-process measurements; no cache flushing, CPU pinning or parallel execution",
        },
        "cases": cases,
    }
    write_json(output / "results.json", summary)
    write_json(output / "expected_vs_observed.json", comparisons)
    write_json(output / "hand_trace.json", trace)
    write_json(output / "cost_models.json", MODEL_NOTES)
    write_json(output / "parallel_trace.json", parallel_filter_trace([int(row["match"]) for row in trace]))
    lines = [
        "L01_T01 | Session 1 baseline",
        "Query: category == laptop AND stock > 0 AND price < INR 60000",
        "20-record expected and observed IDs: " + ", ".join(manual_ids),
        "",
        "       n  matches  comparisons  counted ops  blocks(B=4)  median(us)  correct",
    ]
    for case in cases:
        lines.append(
            f"{case['size']:8,d} {case['matches']:8,d} "
            f"{case['counts']['predicate_comparisons']:12,d} "
            f"{case['counts']['counted_operations']:12,d} "
            f"{case['simulated_input_block_reads']['4']:12,d} "
            f"{case['timing']['median_us']:11.3f}     PASS"
        )
    lines += [
        "", "Counts: visits + evaluated comparisons + output appends; not CPU instructions.",
        "Blocks are simulated cold reads. Parallel bounds are theoretical.",
        "All ID lists and order agree with both the manual fixture and the SQL oracle.",
    ]
    text = "\n".join(lines) + "\n"
    (output / "console.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    print(f"Saved experiment artifacts to: {output}")
    return summary
