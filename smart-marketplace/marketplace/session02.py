"""L02_T02: measured layout access and explicitly simulated hardware traces."""
import cProfile
import io
import pstats
from .catalogue import expand_catalogue, load_catalogue
from .experiments import ROOT, compare_ids, measure, save_result
from .hardware import hardware_traces, one_bit_predictor, pack_catalogue, packed_search, simulate_cache
from .search import linear_search


def run_session(output=None):
    destination = output or ROOT / "results/session02"
    destination.mkdir(parents=True, exist_ok=True)
    fixture = load_catalogue(ROOT / "data/products_20.json")
    cases = []
    for size in (20, 1000, 10000):
        products = expand_catalogue(fixture, size)
        contiguous, scattered = pack_catalogue(products), pack_catalogue(products, scattered=True)
        expected = linear_search(products)
        checks = {"contiguous": compare_ids(expected, packed_search(contiguous)),
                  "scattered": compare_ids(expected, packed_search(scattered)),
                  "eager": compare_ids(expected, packed_search(contiguous, eager=True))}
        functions = {"contiguous": lambda: packed_search(contiguous),
                     "scattered": lambda: packed_search(scattered),
                     "eager_predicates": lambda: packed_search(contiguous, eager=True)}
        vector_note = "NumPy unavailable; SIMD is covered by the four-lane guided trace."
        try:
            import numpy as np
        except ImportError:
            pass
        else:
            data = np.frombuffer(contiguous.records, dtype=np.int64).reshape(-1, 4)
            code = contiguous.category_codes["laptop"]
            def vectorized():
                matches = data[(data[:, 1] == code) & (data[:, 3] > 0) & (data[:, 2] < 60000), 0]
                return [contiguous.ids[int(index)] for index in matches]
            checks["numpy"] = compare_ids(expected, vectorized())
            functions["numpy_vectorized"] = vectorized
            vector_note = f"NumPy {np.__version__}: native array expressions measured; SIMD instruction use was not inspected. Includes conversion of matching indices to IDs; array construction excluded."
        timing = measure(functions)
        caches = {str(kib): {"contiguous": simulate_cache(contiguous.offsets, kib * 1024 // 64),
                            "scattered": simulate_cache(scattered.offsets, kib * 1024 // 64)}
                  for kib in (32, 256, 8192)}
        cases.append({"size": size, "correctness": checks, "timing": timing,
                      "packed_record_bytes": len(contiguous.records) * contiguous.records.itemsize,
                      "offset_bytes": len(contiguous.offsets) * contiguous.offsets.itemsize,
                      "simulated_cache_by_capacity_KiB": caches, "vectorization": vector_note})
    profiler = cProfile.Profile()
    profiler.runcall(lambda: [packed_search(scattered) for _ in range(10)])
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(15)
    (destination / "profile.txt").write_text(stream.getvalue(), encoding="utf-8")
    largest = cases[-1]
    ratio = largest["timing"]["scattered"]["median_us"] / largest["timing"]["contiguous"]["median_us"]
    return save_result(2, {
        "title": "Hardware performance bottlenecks", "cases": cases,
        "input": "Original 20 records repeated deterministically; scattered physical order uses seed 5206. Logical query order is identical.",
        "prediction": "Sequential physical addresses should exploit locality; scattered access may cost more. Python execution overhead can dominate or obscure this effect.",
        "observation": f"At 10000 records scattered/contiguous median ratio was {ratio:.3f}. This is elapsed time, not proof of cache misses or branch stalls.",
        "explanation": "The same offset-indexed loop and three predicates are used for both layouts. Eager evaluation removes predicate short-circuiting but performs all comparisons; it is not guaranteed faster or branch-free machine code. Actual cache counters were not collected.",
        "cache_model": "Three independent cold fully-associative LRU simulations (32/256/8192 KiB); 64-byte lines, 32-byte aligned records. They are illustrative capacities, not measured L1/L2/L3 sizes. Offset and ID arrays, prefetching, associativity and interpreter traffic are excluded.",
        "branch_trace": {"kind": "synthetic one-bit predictor initially predicting false",
                         "grouped": one_bit_predictor([False] * 10 + [True] * 10),
                         "alternating": one_bit_predictor([False, True] * 10)},
        "hardware_traces": hardware_traces(),
        "sources": ["https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/"],
    }, destination)
