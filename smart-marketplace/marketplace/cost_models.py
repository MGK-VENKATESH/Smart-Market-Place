"""Session 1 models. Block counts and parallel traces are SIMULATIONS.

RAM: bounded-size fields and O(1) amortized append; sequential time Theta(n).
External memory: cold, aligned, contiguous fixed-size records, B records/block,
and enough memory for an input block (M >= B). Input reads = ceil(n/B).
Cache oblivious: the same sequential scan never needs to know B or M. Its
input-transfer bound is O(1+n/B); the Python object layout is not this model.
Output writes, CSV/JSON parsing, object headers and cache effects are excluded
from simulated input reads. Writing k output IDs would add O(1+k/B_out) I/Os.
"""

from itertools import accumulate


def simulate_block_reads(size: int, records_per_block: int) -> int:
    """Simulate a cold, one-block buffer while visiting record offsets in order."""
    if type(size) is not int or size < 0:
        raise ValueError("size must be a nonnegative integer")
    if type(records_per_block) is not int or records_per_block <= 0:
        raise ValueError("records_per_block must be a positive integer")
    current_block = None
    reads = 0
    for index in range(size):
        block = index // records_per_block
        if block != current_block:
            reads += 1
            current_block = block
    return reads


def parallel_filter_trace(flags: list[int]) -> dict:
    """Guided stable-compaction trace, computed sequentially for teaching.

    A genuine parallel implementation would compute flags, a work-efficient
    exclusive prefix sum, and scatter matches to distinct output positions.
    That algorithm has W=Theta(n), S=Theta(log n), and O(n) auxiliary space
    for n>=2. The implemented linear search has W=S=Theta(n).
    """
    if any(type(flag) is not int or flag not in (0, 1) for flag in flags):
        raise ValueError("flags must contain integer 0 or 1 values")
    prefix = list(accumulate(flags, initial=0))[:-1]
    return {
        "execution": "sequential guided trace; no parallel runtime was measured",
        "flags": flags,
        "exclusive_prefix": prefix,
        "output_positions": [position if flag else None for flag, position in zip(flags, prefix)],
        "matches": sum(flags),
    }


MODEL_NOTES = {
    "ram": {
        "time": "Theta(n); constant-size query fields and amortized O(1) append",
        "auxiliary_space": "O(1) excluding O(k) returned IDs and O(n) loaded catalogue",
        "count_convention": "visits + evaluated predicate comparisons + output appends",
        "omitted_from_counts": "loop mechanics, field loads, counter updates and interpreter instructions",
    },
    "external_memory": {
        "input_reads": "ceil(n/B), cold aligned scan; B is records per block, M >= B",
        "output_writes": "excluded; add O(1+k/B_out) if k result IDs are written externally",
        "layout": "hypothetical contiguous fixed-size records, not Python objects or JSON bytes",
    },
    "cache_oblivious": {
        "input_transfers": "O(1+n/B), without using B or M in the search algorithm",
        "interpretation": "sequential locality works across block sizes; no hardware misses were measured",
    },
    "parallel": {
        "implemented_baseline": "W=Theta(n), S=Theta(n); sequential code has no parallel speedup",
        "pram": "synchronous shared-memory processors; constant-time word operations; ideal memory access",
        "predicate_only": "with p processors, ceil(n/p) record rounds up to constant predicate cost",
        "compact_output": "flags + work-efficient prefix sum + distinct-position scatter",
        "parallel_design": "W=Theta(n), S=Theta(log n), auxiliary space O(n), for n>=2",
        "bounds": "T_p >= max(W/p,S); an ideal greedy scheduler gives T_p <= W/p + S",
        "parallelism": "W/S=Theta(n/log n); full-query time O(n/p+log n) under the stated model",
        "limitations": "theory only; excludes scheduling, communication, bandwidth and Python overhead",
    },
    "equal_big_o": (
        "Two Theta(n) scans can have different constants, field layouts, cache misses, "
        "branch behavior, interpreter overhead and memory bandwidth. Predicate order "
        "also changes short-circuit work. Big O describes growth, not elapsed seconds."
    ),
    "sources": [
        "Course session plan, Session 1 (page 2)",
        "https://courses.csail.mit.edu/6.854/16/Notes/n28-external.html",
        "https://jshun.csail.mit.edu/6506-f25/lectures/lecture2.pdf",
    ],
}
