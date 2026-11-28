"""Shared repeatable measurements; never mix profiler/simulator time with timing."""

import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import timeit
import tracemalloc
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent


def measure(functions, samples=7, target_seconds=0.005):
    """Warm, calibrated batches; rotate ordering to reduce systematic order bias."""
    timers, batches, raw = {}, {}, {}
    for name, function in functions.items():
        function()
        timers[name] = timeit.Timer(function)
        batch = 1
        while timers[name].timeit(number=batch) < target_seconds and batch < 65536:
            batch *= 2
        batches[name], raw[name] = batch, []
    rng = random.Random(5206)
    for _ in range(samples):
        order = list(functions)
        rng.shuffle(order)
        for name in order:
            raw[name].append(timers[name].timeit(number=batches[name]) * 1e6 / batches[name])
    return {name: {
        "median_us": statistics.median(values), "min_us": min(values), "max_us": max(values),
        "samples_us": values, "batch_size": batches[name],
    } for name, values in raw.items()}


def peak_bytes(function):
    """Additional peak Python allocation during a separate, untimed call."""
    gc.collect()
    tracemalloc.start()
    try:
        result = function()
        _, peak = tracemalloc.get_traced_memory()
        del result
        return peak
    finally:
        tracemalloc.stop()


def compare_ids(expected, observed):
    if expected != observed:
        raise AssertionError("Expected and observed IDs/order differ")
    digest = hashlib.sha256(json.dumps(observed).encode()).hexdigest()
    return {"equal": True, "count": len(observed), "ids_sha256": digest,
            "expected_first_20": expected[:20], "observed_first_20": observed[:20]}


def save_result(session, result, output=None):
    output = Path(output) if output else ROOT / "results" / f"session{session:02d}"
    output.mkdir(parents=True, exist_ok=True)
    result.update({
        "artifact": f"L{session:02d}_T{session:02d}", "session": session, "status": "passed",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "os": platform.platform(),
                        "processor": platform.processor(), "logical_cpus": os.cpu_count()},
        "fixture_sha256": hashlib.sha256((ROOT / "data/products_20.json").read_bytes()).hexdigest(),
        "timing_protocol": "Warm-process calibrated batches, 7 samples in seeded shuffled order; median in microseconds. timeit disables cyclic GC. No CPU pinning/cache flushing. Parsing, profiling and tracing excluded unless explicitly named.",
    })
    # Write then replace so dashboard readers never see a half-written JSON file.
    temporary = output / "results.tmp"
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output / "results.json")
    print(f"Session {session}: PASS | {result['title']} | {output}")
    return result
