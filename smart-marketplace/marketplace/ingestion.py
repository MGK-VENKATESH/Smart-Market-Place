"""Module 1 integration: event buffer, duplicate review and exact search."""
from .duplicates import find_duplicates, naive_duplicates
from .events import DoublingBuffer
from .query_engines import repeated_scan


def ingest_and_search(products, events, queries, optimized=True):
    buffer = DoublingBuffer()
    for event in events:
        buffer.append(event)
    duplicates = find_duplicates(products) if optimized else naive_duplicates(products)
    return {"duplicate_of": duplicates["duplicate_of"],
            "results": repeated_scan(products, queries),
            "events": list(buffer)}
