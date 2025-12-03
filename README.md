# Retail Insights Assistant

AI-powered retail analytics platform with multi-agent architecture for automated insights and conversational Q&A.

## 🎯 Overview

Enterprise-grade GenAI system that analyzes retail sales data using a 4-agent architecture powered by LangChain and LangGraph. Supports both automated summary generation and conversational Q&A for any analytical question.

**Key Capabilities:**
- 📊 Automated business insights & visualizations
- 💬 Natural language Q&A (any analytical question)
- 🤖 4 specialized AI agents with orchestration
- ⚡ Fast analytics on 180K+ records via DuckDB
- 📈 Scalable to 100GB+ datasets (cloud-ready)

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and navigate
cd retail_insights

# Create conda environment
conda env create -f environment.yml
conda activate retail-insights
```

### 2. Configure API Key

```bash
# Copy template
cp env.template .env

# Edit .env and add your key:
# OPENAI_API_KEY=sk-your-key-here
# or
# GOOGLE_API_KEY=your-gemini-key
```

Get API keys:
- OpenAI: https://platform.openai.com/api-keys
- Google Gemini: https://aistudio.google.com/app/apikey

### 3. Run Application

```bash
python main.py
```

Open browser to: **http://localhost:8501**

---

## 📖 Features

### Summary Mode
- **Automated Dashboards**: Revenue, orders, top categories, regional performance
- **Visualizations**: Interactive charts (Plotly)
- **AI Insights**: LLM-generated business recommendations
- **Metrics**: KPIs with trend analysis

### Q&A Mode
- **Natural Language**: Ask any analytical question
- **Dynamic Queries**: System generates SQL automatically
- **Smart Formatting**: Returns appropriate data types (number, list, dict, boolean)
- **Generic Logic**: No hardcoded queries - works for any question

**Example Questions:**
```
"What are the top 6 selling categories?"
"Which state has the highest revenue?"
"What is the average order value by category?"
"How many orders were cancelled?"
"Show me products with low stock levels"
```

---

## 🏗️ Architecture

### Multi-Agent System

```
User Query → [Agent 1: Query Resolution] → [Agent 2: Data Extraction]
                ↓                              ↓
         Generate SQL                    Execute Query
                ↓                              ↓
         [Agent 3: Validation] → [Agent 4: Synthesis]
                ↓                              ↓
         Quality Checks              Natural Language Response
```

**Agent Details:**

| Agent | Purpose | Technology |
|-------|---------|------------|
| **Query Resolution** | Converts natural language to SQL | LLM + Prompt Engineering |
| **Data Extraction** | Executes queries, retrieves data | DuckDB |
| **Validation** | Quality checks, error handling | Python Logic |
| **Synthesis** | Generates insights & responses | LLM + Context |

**Orchestration:** LangGraph state machine with error handling & retry logic

---

## 📁 Project Structure

```
retail_insights/
├── backend/                    # Core logic
│   ├── agents.py              # 4-agent system (850+ lines)
│   ├── data_processor.py      # DuckDB data layer
│   ├── config.py              # Configuration
│   ├── scalability.py         # 100GB+ support (NEW)
│   └── rag_vector_store.py    # Vector search (NEW)
│
├── frontend/
│   └── app.py                 # Streamlit UI (2 modes)
│
├── data/                      # CSV datasets (180K+ rows)
├── tests/                     # Unit tests
├── scripts/                   # Utilities
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
└── environment.yml            # Conda environment
```

---

## 🛠️ Technology Stack

**Backend:**
- Python 3.10
- LangChain + LangGraph (multi-agent orchestration)
- DuckDB (analytical queries)
- OpenAI GPT-4 / Google Gemini

**Frontend:**
- Streamlit (web UI)
- Plotly (interactive charts)
- Pandas (data manipulation)

**Scalability (Optional):**
- Dask (10-50GB datasets)
- PySpark (50GB+ datasets)
- Redis (distributed caching)
- ChromaDB/FAISS (vector search)
- S3/GCS/Azure (cloud storage)

---

## 💡 Usage Examples

### Basic Usage

```python
from backend.agents import MultiAgentRetailAssistant

# Initialize
assistant = MultiAgentRetailAssistant(
    api_key="your-key",
    provider="OpenAI"  # or "Google Gemini"
)

# Generate summary
summary = assistant.get_summary()
print(summary)

# Ask questions
answer = assistant.process_query("What are the top 5 selling categories?")
print(answer)
```

### With Caching (80% Cost Savings)

```python
assistant = MultiAgentRetailAssistant(
    api_key="your-key",
    provider="OpenAI",
    enable_caching=True  # ← Enable query caching
)

# Get performance metrics
metrics = assistant.get_performance_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']}")
print(f"Total cost: {metrics['total_cost_usd']}")
```

### With RAG (Better Context)

```python
assistant = MultiAgentRetailAssistant(
    api_key="your-key",
    provider="OpenAI",
    enable_caching=True,
    enable_rag=True  # ← Enable vector search
)
```

---

## 📊 Scalability

### Current: Local Deployment (< 1GB)
- DuckDB in-memory
- Single machine
- 5-9 seconds per query

### Tier 2: Cloud-Ready (1-10GB)
- Dask for parallel processing
- Parquet format (10x compression)
- Redis caching
- 0.8-2 seconds per query (with cache)

### Tier 3: Enterprise (100GB+)
- PySpark distributed processing
- BigQuery/Snowflake data warehouse
- Kubernetes auto-scaling
- Vector store for semantic search
- 1-3 seconds per query

**See:** `backend/scalability.py` for implementation details

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required: Choose one
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_API_KEY=your-gemini-key

# Optional
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo
GEMINI_MODEL=gemini-2.5-flash
TEMPERATURE=0.7

# Scalability (optional)
REDIS_URL=redis://localhost:6379
S3_BUCKET=retail-insights
```

---

## 🧪 Testing

```bash
# Run all tests
python tests/test_system.py

# Verify setup
python scripts/setup.py

# See examples
python scripts/example_usage.py
```

---

## 📈 Performance

**Query Performance:**
- Cached queries: < 0.1 seconds
- Uncached queries: 5-9 seconds (includes LLM calls)
- Data loading: 1-2 seconds (first time)

**Cost (with OpenAI GPT-4):**
- Per query: ~$0.08 (without cache)
- Per query: ~$0.016 (with 80% cache hit rate)
- 10,000 queries/month: $160 (with caching)

**Scalability:**
- Current: 180K rows in < 1GB
- Tested: Up to 10GB with Dask
- Designed for: 100GB+ with Spark

---

## 🤝 Development

### Setup Dev Environment

```bash
# Install in development mode
pip install -e .

# Install dev dependencies
pip install pytest black flake8

# Format code
black backend/ frontend/ tests/

# Run linter
flake8 backend/ frontend/
```

### Adding New Features

1. **New Agent**: Add to `backend/agents.py`
2. **New Data Source**: Update `backend/data_processor.py`
3. **New UI Component**: Modify `frontend/app.py`
4. **Tests**: Add to `tests/test_system.py`

---

## 📝 Requirements

**Minimum:**
- Python 3.10+
- 4GB RAM
- OpenAI or Google Gemini API key

**Recommended:**
- 8GB+ RAM
- SSD storage
- Internet connection

---

## 🎓 How It Works

### 1. User asks a question
```
"What are the top 6 selling categories?"
```

### 2. Query Resolution Agent
- Classifies intent: **Ranking**
- Extracts number: **6**
- Generates SQL:
```sql
SELECT Category, SUM(Amount) AS TotalSales 
FROM amazon_sales 
WHERE Category IS NOT NULL 
GROUP BY Category 
ORDER BY TotalSales DESC 
LIMIT 6
```

### 3. Data Extraction Agent
- Executes SQL via DuckDB
- Returns 6 rows with categories + revenue

### 4. Validation Agent
- Checks: Query successful ✓
- Checks: Results returned ✓
- Status: **PASSED**

### 5. Synthesis Agent
- Formats results
- Generates response:
```
**Top Selling Categories:**
1. Set - ₹39,204,124
2. kurta - ₹21,299,547
3. Western Dress - ₹11,216,073
4. Top - ₹5,347,792
5. Ethnic Dress - ₹791,218
6. Saree - ₹450,123
```

---

## 🌟 Key Features

✅ **Generic Q&A** - No hardcoded queries, works for ANY question  
✅ **Dynamic Limits** - Respects user's requested count (top 3, 6, 10, etc.)  
✅ **Multi-Provider** - Supports OpenAI & Google Gemini  
✅ **Performance Monitoring** - Track cost, latency, cache hit rate  
✅ **Scalable** - Ready for 100GB+ datasets  
✅ **Production-Ready** - Error handling, retry logic, fallbacks  

---

## 📚 Additional Resources

- **Architecture Details**: See `docs/ARCHITECTURE.md` for complete system design, multi-agent workflows, and enterprise features
- **Presentation**: See `docs/PRESENTATION.md` for 22-slide comprehensive presentation
- **Project Deliverables**: See `docs/DELIVERABLES.md` for submission checklist

---

## 🐛 Troubleshooting

### "Database is locked"
```bash
# Remove lock files
rm retail_insights.db.wal retail_insights.db-shm
```

### "No module named 'langchain'"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### "API key not found"
```bash
# Check .env file exists and contains:
# OPENAI_API_KEY=sk-...
```

### Slow queries
```python
# Enable caching
assistant = MultiAgentRetailAssistant(enable_caching=True)
```

---

## 📄 License

This project is provided for educational and evaluation purposes.

---

## 🎉 Summary

**This is a production-ready, enterprise-scale GenAI retail analytics system with:**
- 4 specialized AI agents
- Generic Q&A (handles any question)
- Automated insights & visualizations
- Scalable to 100GB+ datasets
- Performance monitoring & cost tracking
- Cloud-ready architecture

**Ready to run, ready to scale, ready for production.**

For questions or support, refer to the inline documentation in the source code.
