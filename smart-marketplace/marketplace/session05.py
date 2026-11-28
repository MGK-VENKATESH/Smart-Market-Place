"""L05_T05: profile a real pipeline, then change only its duplicate stage."""
import cProfile
import io
import pstats
from .catalogue import load_catalogue, save_catalogue
from .duplicates import exact_duplicate_oracle, ingestion_fixture
from .events import synthetic_events
from .experiments import ROOT, measure, peak_bytes, save_result
from .ingestion import ingest_and_search
from .reference import reference_search


def profile_call(function, path):
    profiler = cProfile.Profile()
    result = profiler.runcall(function)
    profiler.dump_stats(str(path.with_suffix(".prof")))
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative")
    stats.print_stats(20)
    path.write_text(stream.getvalue(), encoding="utf-8")
    rows = [{"function": key[2], "file": key[0], "line": key[1], "calls": value[1],
             "self_seconds": value[2], "cumulative_seconds": value[3]}
            for key, value in stats.stats.items()]
    return result, sorted(rows, key=lambda row: row["self_seconds"], reverse=True)[:20]


def run_session(output=None):
    destination = output or ROOT / "results/session05"
    destination.mkdir(parents=True, exist_ok=True)
    products = ingestion_fixture(load_catalogue(ROOT / "data/products_20.json"), 1000)
    save_catalogue(products, destination / "input_products.json")
    events = list(synthetic_events(products, 1000))
    queries = [("laptop", 60000), ("tablet", 30000), ("smartphone", 50000)] * 3
    before = lambda: ingest_and_search(products, events, queries, optimized=False)
    after = lambda: ingest_and_search(products, events, queries, optimized=True)
    first, before_profile = profile_call(before, destination / "before_profile.txt")
    second, after_profile = profile_call(after, destination / "after_profile.txt")
    expected = {"duplicate_of": exact_duplicate_oracle(products),
                "results": [reference_search(products, category, limit) for category, limit in queries],
                "events": events}
    if first != expected or second != expected:
        raise AssertionError("Optimized pipeline changed externally visible results")
    timing = measure({"before": before, "after": after})
    ratio = timing["before"]["median_us"] / timing["after"]["median_us"]
    dominant = before_profile[0]
    return save_result(5, {
        "title": "Profiling-driven optimisation", "size": 1000, "event_count": 1000,
        "queries": queries, "before_profile": before_profile, "after_profile": after_profile,
        "timing": timing, "speedup": ratio,
        "additional_peak_python_bytes": {"before": peak_bytes(before), "after": peak_bytes(after)},
        "correctness": {"full_pipeline_equal": True, "duplicate_count": len(expected["duplicate_of"]),
                        "query_match_counts": [len(ids) for ids in expected["results"]], "events_preserved": True},
        "measured_bottleneck": f"Largest self-time entry before change: {dominant['function']} ({dominant['self_seconds']:.6f} profiler seconds). Full before/after call tables are saved.",
        "one_change": "Replace pairwise unique-description comparisons with seeded 32-bit fingerprint buckets plus exact verification. Event buffering, search queries, input and output contracts are unchanged.",
        "observation": (f"Median speedup = {ratio:.2f}x." if ratio > 1 else f"No speedup observed: median before/after ratio = {ratio:.2f}."),
        "explanation": "Profiling locates work; unprofiled repeated timings evaluate the change. Pairwise deduplication has quadratic worst-case comparisons. Fingerprinting reduces candidate comparisons under its hash assumptions but adds hashing/storage overhead, so small or highly duplicated inputs may not benefit. Cache/branch changes would instead affect constants without changing asymptotic scan growth.",
        "sources": ["https://docs.python.org/3.14/library/profile.html"],
    }, destination)
