"""L06_T06: compare exact engines, amortize build cost, freeze the evaluator."""
import hashlib
import math
from .catalogue import expand_catalogue, load_catalogue
from .experiments import ROOT, compare_ids, measure, peak_bytes, save_result
from .query_engines import CategoryIndex, batched_scan, repeated_scan
from .reference import reference_search
from .search import linear_search

QUERIES = [("laptop", 60000), ("laptop", 40000), ("tablet", 30000),
           ("smartphone", 30000), ("monitor", 20000), ("missing", 60000)]


def run_session(output=None):
    fixture = load_catalogue(ROOT / "data/products_20.json")
    cases = []
    for size in (20, 1000, 10000):
        products = expand_catalogue(fixture, size)
        index = CategoryIndex(products)
        expected = [reference_search(products, category, limit) for category, limit in QUERIES]
        methods = {"repeated_scan": lambda: repeated_scan(products, QUERIES),
                   "one_pass_batch": lambda: batched_scan(products, QUERIES),
                   "category_index": lambda: [index.search(category, limit) for category, limit in QUERIES]}
        checks = {name: [compare_ids(e, o) for e, o in zip(expected, function())]
                  for name, function in methods.items()}
        timing = measure(methods | {"index_build": lambda: CategoryIndex(products),
                                   "single_scan": lambda: linear_search(products),
                                   "single_index": lambda: index.search()})
        build = timing["index_build"]["median_us"]
        scan = timing["repeated_scan"]["median_us"]
        indexed = timing["category_index"]["median_us"]
        break_even_batches = math.floor(build / (scan - indexed)) + 1 if scan > indexed else None
        costs = [{"batches": count, "scan_total_us": count * scan,
                  "index_build_plus_queries_us": build + count * indexed}
                 for count in (1, 10, 100)]
        cases.append({"size": size, "queries_per_batch": len(QUERIES), "correctness": checks,
                      "timing": timing, "estimated_break_even_batches": break_even_batches,
                      "build_amortization": costs,
                      "memory": {"catalogue_peak_python_bytes": peak_bytes(lambda: expand_catalogue(fixture, size)),
                                 "extra_index_peak_python_bytes": peak_bytes(lambda: CategoryIndex(products)),
                                 "scan_result_peak_python_bytes": peak_bytes(methods["repeated_scan"])},
                      "one_batch_choice": min(("repeated_scan", "one_pass_batch", "category_index"),
                                               key=lambda name: timing[name]["median_us"] + (build if name == "category_index" else 0))})
    largest = cases[-1]
    frozen = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in ("marketplace/search.py", "marketplace/reference.py", "data/products_20.json", "data/session01_expected.json")}
    return save_result(6, {
        "title": "Choosing a computational model", "queries": QUERIES, "cases": cases,
        "frozen_baseline_sha256": frozen,
        "baseline_choice": "Keep linear_search as the stable correctness baseline. Offer the immutable category index for repeated queries; rebuild after catalogue updates.",
        "measured_selection": f"At 10000 records, estimated category-index break-even is {largest['estimated_break_even_batches']} batches of six queries (build plus query medians). None means no measured crossover. Estimates are local workload-dependent, not universal thresholds.",
        "complexity": {"scan": "Theta(n) per query, O(k) output", "category_index": "O(n) build and extra references; expected O(1) category lookup plus O(n_category) scan and O(k) output",
                       "one_pass_batch": "Theta(n*q) comparisons worst case; one traversal does not eliminate q predicates",
                       "parallel": "A redesigned filter can have O(n) work and O(log n) span; no parallel timings are claimed. Small n may be dominated by scheduling overhead."},
        "model_choice": "Use RAM costs for these resident objects; I/O models for disk/block movement, cache models for locality, and work/span for a future parallel design. Hashing helps exact category/ID lookup but does not make a price-range filter constant time.",
        "explanation": "For a small or frequently rebuilt catalogue, scan avoids index construction and extra memory. For many queries over an unchanged snapshot, amortized index build cost can be repaid. Choose from measured total workload cost, not Big O alone; Python/object overhead and fixed fixture selectivity limit generalization.",
        "indian_context": ["A quant team may value predictable tail latency more than average throughput.", "An HPC batch workload may justify parallel scheduling and locality-aware placement.", "An Indian marketplace product team must balance query latency against stock updates, index rebuilds and memory."],
    }, output)
