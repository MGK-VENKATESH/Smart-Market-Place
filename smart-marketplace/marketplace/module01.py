"""Run all six sessions sequentially, avoiding concurrent timing experiments."""
import importlib
from .experiments import ROOT
from .session01 import write_json

TITLES = {1: "Computational models", 2: "Hardware bottlenecks", 3: "Amortised analysis",
          4: "Expected complexity", 5: "Profiling and optimisation", 6: "Choosing a model"}


def run_session(number, output=None):
    if number not in TITLES:
        raise ValueError("Module 1 contains sessions 1 through 6")
    module = importlib.import_module(f"marketplace.session{number:02d}")
    return module.run_session(output)


def run_all(output=None, progress=None):
    root = output or ROOT / "results"
    complete = []
    for number in TITLES:
        result = run_session(number, root / f"session{number:02d}")
        complete.append({"session": number, "title": TITLES[number], "status": "passed",
                         "run_utc": result["run_utc"]})
        if progress:
            progress(number, TITLES[number])
    manifest = {"module": 1, "status": "passed", "sessions": complete,
                "hardware_evidence": "Python/NumPy elapsed times measured; cache, predictor, NUMA, GPU and SIMD lane examples explicitly simulated or guided."}
    write_json(root / "module01.json", manifest)
    return manifest
