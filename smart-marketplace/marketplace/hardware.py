"""Session 2: packed storage, controlled access order and explicit teaching models."""

from array import array
from collections import OrderedDict
from dataclasses import dataclass
import random
from .search import validate_query


@dataclass
class PackedCatalogue:
    records: array
    offsets: array
    ids: list
    category_codes: dict


def pack_catalogue(products, scattered=False, seed=5206):
    categories = {name: i for i, name in enumerate(sorted({p.category for p in products}))}
    physical_order = list(range(len(products)))
    if scattered:
        random.Random(seed).shuffle(physical_order)
    records, offsets = array("q"), array("q", [0]) * len(products)
    for physical, logical in enumerate(physical_order):
        p = products[logical]
        records.extend((logical, categories[p.category], p.price, p.stock))
        offsets[logical] = physical * 4
    return PackedCatalogue(records, offsets, [p.id for p in products], categories)


def packed_search(catalogue, category="laptop", max_price=60000, eager=False):
    validate_query(category, max_price)
    code = catalogue.category_codes.get(category, -1)
    data, result = catalogue.records, []
    # Both layouts use exactly the same offset-indexed loop and logical order.
    for offset in catalogue.offsets:
        if eager:
            match = (data[offset + 1] == code) & (data[offset + 3] > 0) & (data[offset + 2] < max_price)
        else:
            match = data[offset + 1] == code and data[offset + 3] > 0 and data[offset + 2] < max_price
        if match:
            result.append(catalogue.ids[data[offset]])
    return result


def simulate_cache(offsets, capacity_lines=512, line_bytes=64, item_bytes=8):
    """Cold fully-associative LRU model for the record region only.

    Each record is four words. With 8-byte words and 64-byte aligned lines,
    a record lies within one line. The offsets/ID arrays and prefetching are omitted.
    """
    if capacity_lines < 1:
        raise ValueError("Cache must hold at least one line")
    cache, misses = OrderedDict(), 0
    for offset in offsets:
        line = offset * item_bytes // line_bytes
        if line not in cache:
            misses += 1
            if len(cache) == capacity_lines:
                cache.popitem(last=False)
        else:
            cache.move_to_end(line)
        cache[line] = True
    return {"accesses": len(offsets), "misses": misses, "hits": len(offsets) - misses}


def one_bit_predictor(outcomes):
    prediction, misses = False, 0
    for outcome in outcomes:
        misses += bool(outcome) != prediction
        prediction = bool(outcome)
    return {"branches": len(outcomes), "mispredictions": misses}


def hardware_traces():
    """Illustrative assumptions only; these are not readings from this computer."""
    local_ns, remote_ns = 80, 160
    accesses = ["local", "remote", "remote", "local", "remote", "local", "remote", "local"]
    byte_count, bandwidth_gbs, launches = 32 * 10000, 12, 10
    h2d_us = byte_count / (bandwidth_gbs * 1e9) * 1e6
    return {
        "kind": "synthetic guided traces; no NUMA/GPU hardware counters measured",
        "numa": {"assumed_local_ns": local_ns, "assumed_remote_ns": remote_ns,
                 "accesses": accesses, "mixed_ns": sum(local_ns if a == "local" else remote_ns for a in accesses),
                 "all_local_ns": len(accesses) * local_ns,
                 "lesson": "Place work near its data; this serial latency sum ignores overlap and bandwidth."},
        "gpu": {"input_bytes": byte_count, "assumed_host_link_GBps": bandwidth_gbs,
                "one_upload_us": h2d_us, "assumed_launch_us": launches,
                "assumed_kernel_us": 4, "result_bytes": 3000 * 8,
                "one_download_us": 3000 * 8 / (bandwidth_gbs * 1e9) * 1e6,
                "hierarchy": "Host RAM -> device global memory; shared memory and registers are on-chip, capacity-limited storage. Coalesced accesses reduce transactions.",
                "lesson": "A fast kernel can lose to transfer and launch overhead. Reuse resident data; these assumed numbers are not this GPU's performance."},
        "simd": {"lanes": 4, "prices": [45000, 62000, 55000, 59999], "stock": [12, 5, 0, 3],
                 "category_mask": [1, 1, 1, 1], "price_mask": [1, 0, 1, 1], "stock_mask": [1, 1, 0, 1],
                 "combined_mask": [1, 0, 0, 1],
                 "lesson": "Independent fixed-width comparisons can use SIMD masks. Python bitwise booleans alone do not prove native SIMD or branch-free machine code."},
    }
