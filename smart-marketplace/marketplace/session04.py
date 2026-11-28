"""L04_T04: force collisions, verify exact content, and vary fingerprint width."""
from dataclasses import replace
from .catalogue import load_catalogue, save_catalogue
from .duplicates import exact_duplicate_oracle, find_duplicates, fingerprint, ingestion_fixture, naive_duplicates
from .experiments import ROOT, measure, save_result


def forced_collision(fixture):
    seen = {}
    for index in range(5):  # Five distinct strings in four buckets guarantees a collision.
        text = f"Synthetic distinct description {index}"
        key = fingerprint(text, bits=2)
        if key in seen:
            left, right = seen[key], text
            return [replace(fixture[0], id="COLLISION-A", description=left),
                    replace(fixture[0], id="COLLISION-B", description=right),
                    replace(fixture[0], id="EXACT-COPY", description=left)]
        seen[key] = text
    raise AssertionError("Pigeonhole collision was not found")


def run_session(output=None):
    destination = output or ROOT / "results/session04"
    fixture = load_catalogue(ROOT / "data/products_20.json")
    collision_products = forced_collision(fixture)
    save_catalogue(collision_products, destination / "collision_fixture.json")
    collision = find_duplicates(collision_products, bits=2)
    expected = {"EXACT-COPY": "COLLISION-A"}
    if collision["duplicate_of"] != expected or collision["unique_descriptions"] != 2:
        raise AssertionError("Unequal colliding descriptions were merged")
    cases = []
    for size in (20, 200, 1000):
        products = ingestion_fixture(fixture, size)
        expected = exact_duplicate_oracle(products)
        naive = naive_duplicates(products)
        if naive["duplicate_of"] != expected:
            raise AssertionError("Naive reference failed")
        widths = []
        for bits in (2, 8, 16, 32):
            result = find_duplicates(products, bits=bits)
            if result["duplicate_of"] != expected:
                raise AssertionError("Fingerprint duplicate mapping failed")
            widths.append({"bits": bits, "comparisons": result["comparisons"],
                           "collision_checks": result["collision_checks"], "correct": True,
                           "expected_duplicate_count": len(expected), "observed_duplicate_count": len(result["duplicate_of"])})
        cases.append({"size": size, "naive_comparisons": naive["comparisons"], "widths": widths})
    save_catalogue(products, destination / "input_products.json")
    timing = measure({"naive_pairwise": lambda: naive_duplicates(products),
                      "fingerprint_32": lambda: find_duplicates(products, bits=32)})
    seeds = []
    for seed in (1, 2, 3, 4, 5):
        result = find_duplicates(products, bits=8, seed=seed)
        if result["duplicate_of"] != expected:
            raise AssertionError("Seed changed exact duplicate decisions")
        seeds.append({"seed": seed, "collision_checks": result["collision_checks"], "correct": True})
    return save_result(4, {
        "title": "Expected complexity and fingerprints", "cases": cases, "timing": timing,
        "collision_demo": {"bits": 2, "texts": [p.description for p in collision_products],
                           "fingerprints": [fingerprint(p.description, 2) for p in collision_products],
                           "expected_duplicate_of": {"EXACT-COPY": "COLLISION-A"}, "observed": collision},
        "seed_experiment": seeds, "expected_duplicate_of": expected,
        "input": "Catalogue-derived descriptions: append a unique listing variant except every tenth description copies its predecessor. Product IDs are retained.",
        "explanation": "A fingerprint match only selects candidates. Exact string equality decides duplicates, so collisions affect work but never merge different text. Results flag duplicate descriptions for review; they do not delete catalogue records.",
        "complexity": "Hashing costs O(total text bytes). Under a uniform-fingerprint assumption each unequal pair collides with probability 2^-b; expected unequal pair collisions among u distinct texts are u*(u-1)/(2*2^b). Bucket verification also includes true duplicates. Adversarial collisions can force quadratic comparisons; exact comparison cost depends on text length.",
        "hash_assumption": "Seeded keyed BLAKE2b truncated to b bits is used as a reproducible practical fingerprint, not claimed to be a proven universal hash family. Python dictionary lookup is expected O(1), not a worst-case guarantee.",
    }, destination)
