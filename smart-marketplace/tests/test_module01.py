from dataclasses import replace
import random
import unittest
from marketplace.catalogue import Product, load_catalogue
from marketplace.duplicates import exact_duplicate_oracle, find_duplicates, fingerprint, ingestion_fixture, naive_duplicates
from marketplace.events import DoublingBuffer, Event, synthetic_events
from marketplace.experiments import ROOT
from marketplace.hardware import one_bit_predictor, pack_catalogue, packed_search, simulate_cache
from marketplace.ingestion import ingest_and_search
from marketplace.query_engines import CategoryIndex, batched_scan, repeated_scan
from marketplace.reference import reference_search
from marketplace.session04 import forced_collision


class ModuleOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = load_catalogue(ROOT / "data/products_20.json")

    def test_layout_and_eager_results_match_oracle(self):
        for products in ([], self.fixture, list(reversed(self.fixture))):
            for scattered in (False, True):
                packed = pack_catalogue(products, scattered=scattered)
                for category, limit in (("laptop", 60000), ("laptop", 60001), ("tablet", 30000), ("unknown", 0)):
                    expected = reference_search(products, category, limit)
                    self.assertEqual(packed_search(packed, category, limit), expected)
                    self.assertEqual(packed_search(packed, category, limit, eager=True), expected)

    def test_same_logical_data_despite_scattered_storage(self):
        packed = pack_catalogue(self.fixture, scattered=True)
        self.assertNotEqual(list(packed.offsets), list(range(0, 80, 4)))
        for logical, offset in enumerate(packed.offsets):
            self.assertEqual(packed.records[offset], logical)
            self.assertEqual(packed.records[offset + 2], self.fixture[logical].price)

    def test_lru_cache_model(self):
        self.assertEqual(simulate_cache([0, 4, 8, 0], capacity_lines=1)["misses"], 3)
        self.assertEqual(simulate_cache([0, 4, 8, 0], capacity_lines=2)["misses"], 2)
        self.assertEqual(simulate_cache([], 1)["misses"], 0)

    def test_branch_predictor_hand_trace(self):
        self.assertEqual(one_bit_predictor([False] * 10 + [True] * 10)["mispredictions"], 1)
        self.assertEqual(one_bit_predictor([False, True] * 10)["mispredictions"], 19)

    def test_buffer_cost_and_order_invariants(self):
        buffer, amortized = DoublingBuffer(), 0
        self.assertEqual(list(buffer), [])
        for i in range(1000):
            trace = buffer.append(i)
            self.assertLessEqual(trace["amortized_cost"], 3)
            self.assertGreaterEqual(trace["accounting_credit"], 0)
            self.assertGreaterEqual(trace["potential"], 0)
            amortized += trace["amortized_cost"]
            self.assertEqual(buffer.total_copies, buffer.capacity - 1)
            self.assertLess(buffer.total_copies, 2 * len(buffer))
        self.assertEqual(list(buffer), list(range(1000)))
        self.assertEqual(amortized, buffer.total_actual + buffer.potential)

    def test_buffer_small_hand_trace(self):
        buffer = DoublingBuffer()
        rows = [buffer.append(i) for i in range(9)]
        self.assertEqual([r["copies"] for r in rows], [0, 1, 2, 0, 4, 0, 0, 0, 8])
        self.assertEqual([r["capacity"] for r in rows], [1, 2, 4, 4, 8, 8, 8, 8, 16])

    def test_event_validation_and_anonymous_replay(self):
        events = list(synthetic_events(self.fixture, 25))
        self.assertTrue(all(a.timestamp_ms < b.timestamp_ms for a, b in zip(events, events[1:])))
        self.assertTrue(all(e.user_id.startswith("anon-") for e in events))
        for args in ((-1, "anon", "view", "P001"), (0, "anon", "invalid", "P001"),
                     (0, "anon", "view", None), (0, "anon", "search", None)):
            with self.assertRaises(ValueError):
                Event(*args)

    def test_forced_collision_does_not_merge_distinct_text(self):
        products = forced_collision(self.fixture)
        self.assertNotEqual(products[0].description, products[1].description)
        self.assertEqual(fingerprint(products[0].description, 2), fingerprint(products[1].description, 2))
        result = find_duplicates(products, 2)
        self.assertEqual(result["duplicate_of"], {"EXACT-COPY": "COLLISION-A"})
        self.assertEqual(result["unique_descriptions"], 2)

    def test_fingerprints_seed_width_unicode_and_empty(self):
        for bits in (1, 2, 8, 32, 64):
            for seed in (0, 1, 5206):
                value = fingerprint("laptop / \u092d\u093e\u0930\u0924", bits, seed)
                self.assertEqual(value, fingerprint("laptop / \u092d\u093e\u0930\u0924", bits, seed))
                self.assertLess(value, 2**bits)
                products = ingestion_fixture(self.fixture, 80)
                self.assertEqual(find_duplicates(products, bits, seed)["duplicate_of"], exact_duplicate_oracle(products))
        self.assertEqual(find_duplicates([])["duplicate_of"], {})
        for bits in (0, 65, True):
            with self.assertRaises(ValueError):
                fingerprint("text", bits)

    def test_duplicate_identity_and_input_preservation(self):
        products = ingestion_fixture(self.fixture, 100)
        snapshot = list(products)
        expected = {products[i].id: products[i - 1].id for i in range(9, 100, 10)}
        self.assertEqual(find_duplicates(products)["duplicate_of"], expected)
        self.assertEqual(naive_duplicates(products)["duplicate_of"], expected)
        self.assertEqual(products, snapshot)

    def test_engines_on_seeded_queries(self):
        rng = random.Random(2026)
        for _ in range(40):
            products = [replace(p, price=rng.randrange(70000), stock=rng.randrange(3)) for p in self.fixture]
            rng.shuffle(products)
            queries = [(rng.choice(["laptop", "tablet", "missing"]), rng.randrange(70000)) for _ in range(8)]
            expected = [reference_search(products, *q) for q in queries]
            index = CategoryIndex(products)
            self.assertEqual(repeated_scan(products, queries), expected)
            self.assertEqual(batched_scan(products, queries), expected)
            self.assertEqual([index.search(*q) for q in queries], expected)

    def test_empty_batch_and_index_snapshot(self):
        self.assertEqual(batched_scan(self.fixture, []), [])
        self.assertEqual(CategoryIndex([]).search(), [])
        original = [self.fixture[0]]
        index = CategoryIndex(original)
        original[0] = replace(original[0], stock=0)
        self.assertEqual(index.search(), ["P001"])
        self.assertEqual(CategoryIndex(original).search(), [])

    def test_integrated_pipeline_before_after(self):
        products = ingestion_fixture(self.fixture, 100)
        events = list(synthetic_events(products, 37))
        queries = [("laptop", 60000), ("laptop", 60001), ("missing", 0)]
        expected = {"duplicate_of": exact_duplicate_oracle(products), "events": events,
                    "results": [reference_search(products, *q) for q in queries]}
        self.assertEqual(ingest_and_search(products, events, queries, False), expected)
        self.assertEqual(ingest_and_search(products, events, queries, True), expected)


if __name__ == "__main__":
    unittest.main()
