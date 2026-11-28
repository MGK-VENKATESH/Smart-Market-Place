"""Session 4: fingerprint candidate buckets with mandatory exact verification.

Duplicate descriptions are flagged for review; catalogue IDs are never merged.
"""

from dataclasses import replace
import hashlib
from .catalogue import expand_catalogue


def fingerprint(text, bits=32, seed=5206):
    if type(bits) is not int or not 1 <= bits <= 64:
        raise ValueError("Fingerprint width must be 1..64 bits")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("Seed must be an unsigned 64-bit integer")
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8, key=seed.to_bytes(8, "little")).digest()
    return int.from_bytes(digest, "little") & ((1 << bits) - 1)


def find_duplicates(products, bits=32, seed=5206):
    fingerprint("", bits, seed)  # Validate even for empty input.
    buckets, duplicate_of = {}, {}
    comparisons = collisions = 0
    for product in products:
        key = fingerprint(product.description, bits, seed)
        candidates = buckets.setdefault(key, [])
        for candidate in candidates:
            comparisons += 1
            if candidate.description == product.description:
                duplicate_of[product.id] = candidate.id
                break
            collisions += 1
        else:
            candidates.append(product)
    return {"duplicate_of": duplicate_of, "comparisons": comparisons,
            "collision_checks": collisions, "unique_descriptions": sum(map(len, buckets.values())),
            "buckets": len(buckets), "bits": bits, "seed": seed}


def naive_duplicates(products):
    unique, duplicate_of = [], {}
    comparisons = 0
    for product in products:
        for candidate in unique:
            comparisons += 1
            if candidate.description == product.description:
                duplicate_of[product.id] = candidate.id
                break
        else:
            unique.append(product)
    return {"duplicate_of": duplicate_of, "comparisons": comparisons,
            "unique_descriptions": len(unique)}


def exact_duplicate_oracle(products):
    first, duplicates = {}, {}
    for product in products:
        if product.description in first:
            duplicates[product.id] = first[product.description]
        else:
            first[product.description] = product.id
    return duplicates


def ingestion_fixture(fixture, size):
    """Catalogue-derived variants, every tenth description duplicates its predecessor."""
    products = expand_catalogue(fixture, size)
    for index, product in enumerate(products):
        description = (products[index - 1].description if index % 10 == 9
                       else f"{product.description} Listing variant {index}.")
        products[index] = replace(product, description=description)
    return products
