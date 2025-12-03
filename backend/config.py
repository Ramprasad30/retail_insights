import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_PATH = BASE_DIR / "data" / "Sales Dataset" / "Sales Dataset"
VECTOR_STORE_PATH = BASE_DIR / "vector_store"
DUCKDB_PATH = BASE_DIR / "retail_insights.db"

# Data files
DATA_FILES = {
    "amazon_sales": "Amazon Sale Report.csv",
    "sale_report": "Sale Report.csv",
    "international_sales": "International sale Report.csv",
    "may_2022": "May-2022.csv",
    "pl_march_2021": "P  L March 2021.csv",
    "expense": "Expense IIGF.csv",
    "warehouse": "Cloud Warehouse Compersion Chart.csv"
}

MAX_ITERATIONS = 10
AGENT_TIMEOUT = 300

# Streamlit config
PAGE_TITLE = "Retail Insights Assistant"
PAGE_ICON = "📊"
LAYOUT = "wide"

