import unittest
from marketplace.catalogue import load_catalogue
from marketplace.experiments import ROOT
from marketplace.storefront import browse, inventory_summary


class StorefrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = load_catalogue(ROOT / "data/products_20.json")

    def test_search_and_sort(self):
        found = browse(self.products, query="  CODEBOOK  ")
        self.assertEqual([p.id for p in found], ["P001"])
        rows = browse(self.products, sort="Price: low to high")
        self.assertEqual([p.price for p in rows], sorted(p.price for p in rows))

    def test_stock_and_inclusive_price(self):
        self.assertNotIn("P003", [p.id for p in browse(self.products)])
        self.assertIn("P003", [p.id for p in browse(self.products, in_stock=False)])
        self.assertIn("P006", [p.id for p in browse(self.products, max_price=60000)])
        self.assertNotIn("P006", [p.id for p in browse(self.products, max_price=59999)])

    def test_inventory_metrics(self):
        summary = inventory_summary(self.products)
        self.assertEqual((summary["products"], summary["available"], summary["out_of_stock"],
                          summary["low_stock"], summary["units"]), (20, 15, 5, 5, 123))
        self.assertEqual(len(summary["categories"]), 6)

    def test_empty_and_invalid_price(self):
        self.assertEqual(browse([]), [])
        self.assertEqual(browse(self.products, category="missing"), [])
        with self.assertRaises(ValueError):
            browse(self.products, max_price=-1)


if __name__ == "__main__":
    unittest.main()
