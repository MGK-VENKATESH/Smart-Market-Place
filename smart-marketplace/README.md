# Smart marketplace

A local inventory dashboard for exploring tech products, saving favourites and monitoring catalogue availability.

## Start the website

Open Terminal (macOS/Linux) or PowerShell (Windows) in this project folder:

~~~bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run streamlit_app.py
~~~

Open **http://127.0.0.1:8501**. You can also run the included
run_dashboard.ps1 launcher.

## Website features

- **Inventory overview** shows current availability, category mix and the most-stocked product in each category.
- **Browse products:** search names/descriptions/IDs, filter category and budget,
  include unavailable products, and sort by price or name.
- **Product details:** price, description, availability and quantity.
- **Saved products:** save and remove favourites across pages.
- **Catalogue insights:** category coverage, stock levels, low-stock alerts and
  exact duplicate-description checks.

Prices are in INR. The website's maximum-price filter is inclusive.
Saved products persist in the current browser connection; there is no account
or persistent shopping cart. The site is a local catalogue, with no payment flow.

## Data

The storefront uses the original **20 products in data/products_20.json**,
covering six categories. The repeated catalogues used by developer performance
tools are not displayed as separate retail products.

The sidebar identifies the sample catalogue and its INR currency.

The search and duplicate-checking implementations remain reusable Python code.
Existing CLI developer utilities and their recorded results remain available
through python -m marketplace --help; the website does not expose them.

## Checks

~~~powershell
python -m unittest discover -s tests -v
~~~

The tests cover query boundaries, saved-product behavior, category navigation,
product details, inventory totals and the underlying algorithm implementations.

## Main files

- streamlit_app.py: application entry point and navigation.
- app_pages/: overview, browsing, saved products and catalogue insights.
- marketplace/storefront.py: filtering and catalogue summaries.
- marketplace/dashboard.py: cached data and reusable product cards.
- data/products_20.json: storefront data source.
- assets/workspace.css: responsive dashboard styling.

## macOS Java Runtime message

This is a Python/Streamlit application and does **not** require Java to run.
The macOS message "Unable to locate a Java Runtime" is from a separate
command or application that attempted to launch Java; it is not the cause of
the Streamlit chart error. Start this project with the Python commands above.

If another tool you use genuinely requires Java, install a JDK separately.
For an Apple Silicon Mac with Homebrew:

~~~bash
brew install openjdk@21
sudo ln -sfn "$(brew --prefix)/opt/openjdk@21/libexec/openjdk.jdk" \
  /Library/Java/JavaVirtualMachines/openjdk-21.jdk
java -version
~~~
