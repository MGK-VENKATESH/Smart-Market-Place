from dataclasses import replace
import json
from pathlib import Path
import random
import tempfile
import unittest

from marketplace.catalogue import Product, expand_catalogue, load_catalogue, save_catalogue
from marketplace.cost_models import parallel_filter_trace, simulate_block_reads
from marketplace.reference import reference_search
from marketplace.search import instrumented_search, linear_search

ROOT = Path(__file__).resolve().parent.parent


class SessionOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = load_catalogue(ROOT / "data" / "products_20.json")
        cls.expected = ["P001", "P004", "P007", "P011", "P014", "P018"]

    def test_manual_expected_ids_and_order(self):
        self.assertEqual(linear_search(self.products), self.expected)
        self.assertEqual(reference_search(self.products), self.expected)

    def test_price_limit_is_exclusive(self):
        boundary = replace(self.products[0], price=60_000, stock=1)
        self.assertEqual(linear_search([boundary]), [])
        self.assertEqual(linear_search([replace(boundary, price=59_999)]), [boundary.id])
        self.assertEqual(linear_search([replace(boundary, price=60_001)]), [])

    def test_zero_stock_is_excluded(self):
        self.assertEqual(linear_search([replace(self.products[0], stock=0)]), [])

    def test_empty_input(self):
        self.assertEqual(linear_search([]), [])
        self.assertEqual(reference_search([]), [])
        self.assertEqual(instrumented_search([])[1].counted_operations, 0)

    def test_no_match_and_exact_category(self):
        self.assertEqual(linear_search(self.products, "Laptop"), [])
        self.assertEqual(linear_search(self.products, max_price=0), [])
        self.assertEqual(linear_search(self.products, "tablet"), ["P008"])

    def test_all_match(self):
        products = [replace(self.products[0], id=f"X{i}") for i in range(7)]
        self.assertEqual(linear_search(products), [p.id for p in products])
        self.assertEqual(instrumented_search(products)[1].predicate_comparisons, 21)

    def test_input_order_is_preserved(self):
        self.assertEqual(linear_search(list(reversed(self.products))), list(reversed(self.expected)))

    def test_manual_operation_counts(self):
        ids, counts = instrumented_search(self.products)
        self.assertEqual(ids, self.expected)
        self.assertEqual((counts.records_visited, counts.category_comparisons,
                          counts.stock_comparisons, counts.price_comparisons,
                          counts.output_appends), (20, 20, 14, 10, 6))
        self.assertEqual(counts.predicate_comparisons, 44)
        self.assertEqual(counts.counted_operations, 70)

    def test_three_sizes_against_manual_pattern_and_sql(self):
        for size in (20, 1000, 10000):
            with self.subTest(size=size):
                products = expand_catalogue(self.products, size)
                expected = [p.id for i, p in enumerate(products) if self.products[i % 20].id in self.expected]
                self.assertEqual(linear_search(products), expected)
                self.assertEqual(reference_search(products), expected)
                self.assertEqual(instrumented_search(products)[0], expected)

    def test_expansion_is_deterministic_and_unique(self):
        first = expand_catalogue(self.products, 21)
        self.assertEqual(first, expand_catalogue(self.products, 21))
        self.assertEqual(first[-1].id, "P001_R0001")
        self.assertEqual(len({p.id for p in first}), 21)
        self.assertEqual(expand_catalogue([], 0), [])
        with self.assertRaises(ValueError):
            expand_catalogue([], 1)

    def test_block_reads_boundaries(self):
        for size, block_size, expected in ((0, 4, 0), (1, 4, 1), (4, 4, 1),
                                            (5, 4, 2), (20, 4, 5), (1000, 16, 63),
                                            (10000, 64, 157)):
            with self.subTest(size=size, block_size=block_size):
                self.assertEqual(simulate_block_reads(size, block_size), expected)
        for size, block_size in ((-1, 4), (20, 0), (20, -1)):
            with self.assertRaises(ValueError):
                simulate_block_reads(size, block_size)

    def test_parallel_trace_compacts_in_order(self):
        trace = parallel_filter_trace([1, 0, 0, 1, 0, 1])
        self.assertEqual(trace["exclusive_prefix"], [0, 1, 1, 1, 2, 2])
        self.assertEqual(trace["output_positions"], [0, None, None, 1, None, 2])
        self.assertEqual(parallel_filter_trace([])["matches"], 0)
        with self.assertRaises(ValueError):
            parallel_filter_trace([2])

    def test_catalogue_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "products.json"
            save_catalogue(self.products, path)
            self.assertEqual(load_catalogue(path), self.products)

    def test_loader_rejects_duplicate_ids_and_invalid_schema(self):
        row = {"id": "A", "title": "T", "description": "D", "category": "laptop",
               "price": 10, "stock": 1, "version": 1}
        bad_inputs = [[row, row], [row | {"price": -1}], [row | {"stock": 1.5}],
                      [row | {"price": True}], [row | {"version": 0}],
                      [row | {"id": ""}], [row | {"extra": 1}], {}, [None]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for value in bad_inputs:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_catalogue(path)

    def test_invalid_queries(self):
        for category, price in (("", 60000), ("laptop", -1), ("laptop", 1.5), ("laptop", True)):
            with self.subTest(category=category, price=price):
                with self.assertRaises(ValueError):
                    linear_search(self.products, category, price)

    def test_seeded_queries_against_independent_oracle(self):
        rng = random.Random(520601)
        for trial in range(100):
            products = [Product(str(i), "Synthetic", "Test record", rng.choice(["laptop", "tablet", "phone"]),
                                rng.choice([0, 49999, 59999, 60000, 60001, 80000]),
                                rng.randrange(4), 1) for i in range(rng.randrange(101))]
            category = rng.choice(["laptop", "tablet", "phone", "missing"])
            limit = rng.choice([0, 50000, 60000, 60001, 90000])
            with self.subTest(trial=trial):
                expected = reference_search(products, category, limit)
                self.assertEqual(linear_search(products, category, limit), expected)
                self.assertEqual(instrumented_search(products, category, limit)[0], expected)


if __name__ == "__main__":
    unittest.main()
