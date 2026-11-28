"""Product-facing website behavior and copy checks."""
import unittest
from streamlit.testing.v1 import AppTest
from marketplace.experiments import ROOT


class WebsiteTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=15).run()

    def product_ids(self, app):
        return [button.key.removeprefix("details_browse_") for button in app.button
                if button.key and button.key.startswith("details_browse_")]

    def test_pages_render_without_coursework_references(self):
        app = self.app()
        for page in ("overview", "catalogue", "saved", "insights"):
            with self.subTest(page=page):
                app.switch_page(f"app_pages/{page}.py").run()
                self.assertFalse(app.exception)
                text = " ".join(str(element.value) for kind in ("title", "subheader", "caption", "markdown")
                                for element in app.get(kind)).lower()
                for forbidden in ("module", "session", "algorithm", "benchmark", "26cs5206", "baseline", "experiment"):
                    self.assertNotIn(forbidden, text)

    def test_search_inclusive_budget_and_empty_state(self):
        app = self.app().switch_page("app_pages/catalogue.py").run()
        self.assertEqual(len(self.product_ids(app)), 15)
        app.selectbox(key="browse_category").select("laptop").run()
        app.number_input(key="maximum_price").set_value(60000).run()
        self.assertEqual(len(self.product_ids(app)), 7)
        self.assertIn("P006", self.product_ids(app))
        app.number_input(key="maximum_price").set_value(59999).run()
        self.assertEqual(self.product_ids(app), ["P001", "P004", "P007", "P011", "P014", "P018"])
        app.number_input(key="maximum_price").set_value(0).run()
        self.assertFalse(self.product_ids(app))
        self.assertIn("No products found", [item.value for item in app.subheader])
        self.assertFalse(app.exception)

    def test_home_category_opens_filtered_products(self):
        app = self.app()
        app.button(key="category_tablet").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="browse_category").value, "tablet")
        self.assertEqual(self.product_ids(app), ["P008"])

    def test_save_and_remove_across_pages(self):
        app = self.app()
        app.button(key="save_featured_P001").click().run()
        self.assertIn("P001", app.session_state.saved_products)
        app.switch_page("app_pages/saved.py").run()
        self.assertTrue(app.button(key="details_saved_P001"))
        app.button(key="save_saved_P001").click().run()
        self.assertNotIn("P001", app.session_state.saved_products)
        self.assertIn("Make room for your favourites", [item.value for item in app.subheader])
        self.assertFalse(app.exception)

    def test_product_details_open(self):
        app = self.app()
        app.button(key="details_featured_P001").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Product ID: P001" in item.value for item in app.caption))


if __name__ == "__main__":
    unittest.main()
