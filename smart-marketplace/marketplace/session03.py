"""L03_T03: measured copies and accounting/potential derivations for event storage."""
from dataclasses import asdict
from .catalogue import load_catalogue
from .events import DoublingBuffer, synthetic_events
from .experiments import ROOT, save_result
from .session01 import write_json


def run_session(output=None):
    destination = output or ROOT / "results/session03"
    products = load_catalogue(ROOT / "data/products_20.json")
    events = list(synthetic_events(products, 20))
    write_json(destination / "input_events.json", [asdict(event) for event in events])
    small = DoublingBuffer()
    trace = [small.append(event) for event in events]
    if list(small) != events:
        raise AssertionError("Buffer changed event order/content")
    cases = []
    for size in (0, 1, 2, 4, 8, 16, 20, 1000, 10000):
        buffer = DoublingBuffer()
        worst = 0
        amortized_sum = 0
        for event in synthetic_events(products, size):
            row = buffer.append(event)
            worst = max(worst, row["actual_cost"])
            amortized_sum += row["amortized_cost"]
            if row["potential"] < 0 or row["accounting_credit"] < 0 or row["amortized_cost"] > 3:
                raise AssertionError("Amortized bound failed")
        expected_capacity = (1 << (size - 1).bit_length()) if size else 0
        expected_copies = max(0, expected_capacity - 1)
        if buffer.total_copies != expected_copies or buffer.capacity != expected_capacity:
            raise AssertionError("Geometric copy-count formula failed")
        if amortized_sum != buffer.total_actual + buffer.potential:
            raise AssertionError("Potential telescoping identity failed")
        cases.append({"size": size, "capacity": buffer.capacity, "expected_copies": expected_copies,
                      "observed_copies": buffer.total_copies, "total_cost": buffer.total_actual,
                      "worst_append_cost": worst, "amortized_sum": amortized_sum, "correct": True})
    return save_result(3, {
        "title": "Amortised event storage", "trace": trace, "cases": cases,
        "expected_vs_observed": {"event_order_preserved": True, "stored_events": len(small)},
        "cost_convention": "One unit per inserted element and copied existing element; allocation/empty-slot initialization excluded. No measured latency is inferred from these counts.",
        "accounting": "Charge 3 per append; bank = 3*n - (n + copies). The bank never becomes negative. Saved credits pay for future copies; even an adversarial insertion sequence has linear total cost.",
        "potential": "Phi = 2*n - capacity, initially 0. First insertion has amortized cost 2. A non-resizing insertion costs 1 with delta Phi = 2. Doubling a full c-slot buffer costs c+1 with delta Phi = 2-c. Both therefore have amortized cost 3.",
        "aggregate": "For n>0 final capacity C is the next power of two >=n. Copies = 1+2+...+C/2 = C-1 < 2*n. Total stores/copies = n+C-1 <3*n. A single resizing append still costs Theta(n).",
        "explanation": "Amortized analysis bounds every valid operation sequence without a probability distribution. Average-case analysis instead averages over a specified distribution of inputs. Buffer memory grows with event count; bounded streaming state is a later module.",
        "sources": ["https://ocw.mit.edu/courses/6-046j-introduction-to-algorithms-sma-5503-fall-2005/0a02bc84e917b9aeddaf69c8dc151a6f_lec13.pdf"],
    }, destination)
