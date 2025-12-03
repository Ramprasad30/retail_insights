# 🏗️ Retail Insights Assistant - System Architecture

**Production-Ready GenAI Multi-Agent System for Retail Analytics**

## Table of Contents

1. [System Overview](#system-overview)
2. [Multi-Agent Architecture](#multi-agent-architecture)
3. [Data Flow](#data-flow)
4. [Component Details](#component-details)
5. [Scalability Architecture (100GB+)](#scalability-architecture)
6. [Enterprise Features](#enterprise-features)
7. [Cost Analysis](#cost-analysis)
8. [Performance Considerations](#performance-considerations)

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Streamlit Web Application                       │  │
│  │  • Summary Dashboard  • Q&A Chat  • Visualizations       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                   APPLICATION LOGIC LAYER                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Multi-Agent System (LangGraph)                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │  Query   │→ │   Data   │→ │Validation│→ │Synthesis │ │  │
│  │  │Resolution│  │Extraction│  │  Agent   │  │  Agent   │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LLM Integration (OpenAI GPT-4)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ SQL Queries
┌────────────────────────────▼────────────────────────────────────┐
│                      DATA PROCESSING LAYER                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              DuckDB Analytical Database                   │  │
│  │  • In-memory processing  • Columnar storage              │  │
│  │  • SQL query engine      • Analytical functions          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ Data Loading
┌────────────────────────────▼────────────────────────────────────┐
│                       DATA STORAGE LAYER                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │  Amazon    │  │International│  │ Inventory  │  │   P&L    │ │
│  │   Sales    │  │   Sales     │  │   Data     │  │  Data    │ │
│  │ (128K rows)│  │  (37K rows) │  │  (9K rows) │  │(1K rows) │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘ │
│                     CSV Files on Disk                            │
└─────────────────────────────────────────────────────────────────┘
```

## Multi-Agent Architecture

### Agent Communication Flow

```
                      ┌─────────────────┐
                      │   User Query    │
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │  Shared State   │
                      │  (AgentState)   │
                      └────────┬────────┘
                               │
        ╔══════════════════════▼═══════════════════════╗
        ║       AGENT 1: Query Resolution Agent        ║
        ╠══════════════════════════════════════════════╣
        ║ Input:  User natural language query          ║
        ║ Process:                                      ║
        ║   1. Parse intent and context                ║
        ║   2. Identify required tables/columns        ║
        ║   3. Generate SQL query                      ║
        ║   4. Determine query type (summary/qa)       ║
        ║ Output: SQL query string, query metadata     ║
        ╚══════════════════════════════════════════════╝
                               │
                      ┌────────▼────────┐
                      │  Update State   │
                      │  sql_query      │
                      │  query_type     │
                      └────────┬────────┘
                               │
        ╔══════════════════════▼═══════════════════════╗
        ║      AGENT 2: Data Extraction Agent          ║
        ╠══════════════════════════════════════════════╣
        ║ Input:  SQL query, database connection       ║
        ║ Process:                                      ║
        ║   1. Execute SQL via DuckDB                  ║
        ║   2. Handle errors and edge cases            ║
        ║   3. Limit results (pagination)              ║
        ║   4. Format data structure                   ║
        ║ Output: DataFrame / Dictionary of results    ║
        ╚══════════════════════════════════════════════╝
                               │
                      ┌────────▼────────┐
                      │  Update State   │
                      │  data_result    │
                      └────────┬────────┘
                               │
        ╔══════════════════════▼═══════════════════════╗
        ║        AGENT 3: Validation Agent             ║
        ╠══════════════════════════════════════════════╣
        ║ Input:  Query results, expected schema       ║
        ║ Process:                                      ║
        ║   1. Check for errors                        ║
        ║   2. Validate data availability              ║
        ║   3. Verify data structure                   ║
        ║   4. Quality assurance checks                ║
        ║ Output: Validation status (PASS/WARN/FAIL)   ║
        ╚══════════════════════════════════════════════╝
                               │
                      ┌────────▼────────┐
                      │  Update State   │
                      │validation_status│
                      └────────┬────────┘
                               │
        ╔══════════════════════▼═══════════════════════╗
        ║        AGENT 4: Synthesis Agent              ║
        ╠══════════════════════════════════════════════╣
        ║ Input:  Validated data, user query, context  ║
        ║ Process:                                      ║
        ║   1. Analyze data patterns                   ║
        ║   2. Generate insights                       ║
        ║   3. Format response in natural language     ║
        ║   4. Add business context                    ║
        ║ Output: Human-readable response with insights║
        ╚══════════════════════════════════════════════╝
                               │
                      ┌────────▼────────┐
                      │  Final Response │
                      │  to User        │
                      └─────────────────┘
```

### State Management

```python
class AgentState(TypedDict):
    """Shared state across all agents"""
    messages: List[BaseMessage]      # Conversation history
    user_query: str                  # Original user question
    query_type: str                  # 'summary' or 'qa'
    sql_query: str                   # Generated SQL
    data_result: Any                 # Query results
    validation_status: str           # 'PASSED', 'WARNING', 'FAILED'
    final_response: str              # Final answer
    schema_info: Dict                # Database schema
    summary_stats: Dict              # Pre-computed statistics
    iteration: int                   # Current iteration count
```

### LangGraph Workflow Definition

```python
from langgraph.graph import StateGraph, END

# Create workflow graph
workflow = StateGraph(AgentState)

# Add agent nodes
workflow.add_node("query_resolution", query_resolution_agent)
workflow.add_node("data_extraction", data_extraction_agent)
workflow.add_node("validation", validation_agent)
workflow.add_node("synthesis", synthesis_agent)

# Define linear workflow
workflow.set_entry_point("query_resolution")
workflow.add_edge("query_resolution", "data_extraction")
workflow.add_edge("data_extraction", "validation")
workflow.add_edge("validation", "synthesis")
workflow.add_edge("synthesis", END)

# Compile to executable
graph = workflow.compile()
```

## Data Flow

### Summary Mode Flow

```
User clicks "Generate Summary"
        │
        ├─> Load all datasets into DuckDB
        │   ├─> Amazon Sales (128K rows)
        │   ├─> International Sales (37K rows)
        │   └─> Inventory (9K rows)
        │
        ├─> Execute pre-defined aggregation queries
        │   ├─> Total revenue, orders, metrics
        │   ├─> Top categories analysis
        │   ├─> Regional performance
        │   └─> Status distribution
        │
        ├─> Generate visualizations
        │   ├─> Bar charts (categories, states)
        │   ├─> Pie charts (status distribution)
        │   └─> Metric cards
        │
        ├─> Pass to Multi-Agent System
        │   └─> Synthesis Agent generates insights
        │
        └─> Display dashboard + AI insights
```

### Q&A Mode Flow

```
User enters question: "What are top selling categories?"
        │
        ├─> Query Resolution Agent
        │   ├─> Analyze intent: "top selling" = revenue/quantity ranking
        │   ├─> Identify table: amazon_sales
        │   ├─> Identify columns: Category, Amount
        │   └─> Generate SQL:
        │       SELECT Category, COUNT(*) as orders, 
        │              SUM(Amount) as revenue
        │       FROM amazon_sales
        │       GROUP BY Category
        │       ORDER BY revenue DESC
        │       LIMIT 5
        │
        ├─> Data Extraction Agent
        │   ├─> Execute SQL query
        │   ├─> Retrieve results (5 rows)
        │   └─> Format as dictionary
        │
        ├─> Validation Agent
        │   ├─> Check: Query executed successfully ✓
        │   ├─> Check: Results returned ✓
        │   ├─> Check: Data structure valid ✓
        │   └─> Status: PASSED
        │
        ├─> Synthesis Agent
        │   ├─> Analyze: Top category is "Kurta" with ₹15.2M
        │   ├─> Context: Represents 29% of total revenue
        │   ├─> Insight: Strong performance in traditional wear
        │   └─> Generate natural language response
        │
        └─> Display formatted answer to user
```

## Component Details

### 1. Data Processor (DuckDB)

**File:** `data_processor.py`

**Responsibilities:**
- Load CSV files into DuckDB tables
- Provide schema information
- Execute SQL queries
- Generate summary statistics
- Handle data search

**Key Methods:**

```python
class RetailDataProcessor:
    def load_data() -> Dict[str, Any]
        # Load all CSV files into DuckDB tables
        
    def execute_query(query: str) -> pd.DataFrame
        # Execute SQL and return results
        
    def get_schema_info() -> Dict[str, List[str]]
        # Return table schemas
        
    def get_summary_statistics() -> Dict[str, Any]
        # Pre-computed aggregate statistics
```

**DuckDB Advantages:**
- In-memory processing (fast)
- Columnar storage (efficient aggregations)
- SQL interface (familiar)
- Pandas integration (seamless)
- No server required (embedded)

### 2. Multi-Agent System (LangGraph)

**File:** `agents.py`

**Architecture Pattern:** Agent-Based Workflow

**Design Principles:**
1. **Single Responsibility**: Each agent has one clear purpose
2. **Sequential Processing**: Linear workflow with state passing
3. **Error Handling**: Each agent can fail gracefully
4. **State Immutability**: Agents update state, don't mutate

**Agent Specializations:**

| Agent | LLM Usage | Data Access | Output |
|-------|-----------|-------------|--------|
| Query Resolution | Yes (SQL generation) | Schema only | SQL query |
| Data Extraction | No | Full database | Raw data |
| Validation | No | Result set | Status |
| Synthesis | Yes (insight generation) | Query results | Natural language |

### 3. Streamlit UI

**File:** `app.py`

**Architecture Pattern:** Component-Based UI

**Components:**
1. **Sidebar**: Configuration and mode selection
2. **Main Panel**: Content display
3. **Chat Interface**: Q&A history
4. **Dashboard**: Summary visualizations

**State Management:**
```python
# Session state for chat history
st.session_state.messages = []

# Cached resources (expensive operations)
@st.cache_resource
def initialize_assistant(api_key):
    return MultiAgentRetailAssistant(api_key)
```

### 4. Configuration Management

**File:** `config.py`

**Centralized Configuration:**
- API keys (environment variables)
- Model parameters
- Data paths
- System limits
- Feature flags

## Scalability Architecture (100GB+)

### Phase 1: Current Architecture (Up to 10GB)

```
Local Machine
├── CSV Files (disk)
├── DuckDB (in-memory)
├── Python Application
└── Streamlit UI
```

**Limitations:**
- Single machine memory
- No horizontal scaling
- Manual data updates
- Limited concurrency

### Phase 2: Cloud-Ready Architecture (10GB - 100GB)

```
┌─────────────────────────────────────────────┐
│         Application Tier (Docker)           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Streamlit │  │  Agents  │  │  Data    │ │
│  │    UI    │  │  System  │  │Processor │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│            Redis Cache Layer                │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         DuckDB / Trino Query Engine         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Object Storage (S3/GCS/Azure)          │
│         Parquet Files (partitioned)         │
└─────────────────────────────────────────────┘
```

**Improvements:**
- Containerized deployment
- Result caching
- Parquet format (10x smaller)
- Partitioned storage

### Phase 3: Enterprise Architecture (100GB+)

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  App Instance  │  │  App Instance  │  │  App Instance  │
│   (Container)  │  │   (Container)  │  │   (Container)  │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        └────────────────────┼────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │   Redis Cluster (Cache)     │
              └──────────────┬──────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│   Pinecone     │  │   BigQuery     │  │    Spark       │
│ (Vector Store) │  │  (Data Warehouse)│ │  (Processing)  │
└────────────────┘  └───────┬────────┘  └────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Cloud Storage  │
                    │ (Data Lake)     │
                    │  Delta Lake     │
                    └─────────────────┘
```

**Key Components:**

#### A. Data Ingestion Pipeline

```
Raw Data Sources
    ↓
Apache Kafka / Cloud Pub/Sub (streaming)
    ↓
Apache Spark / Dask (processing)
    ├─> Validation & Cleaning
    ├─> Schema Enforcement
    ├─> Partitioning Strategy
    └─> Format Conversion (Parquet/Delta)
    ↓
Cloud Storage (S3/GCS/Azure)
    ├─> Raw Zone (immutable)
    ├─> Curated Zone (cleaned)
    └─> Aggregated Zone (pre-computed)
    ↓
Data Warehouse (BigQuery/Snowflake)
```

#### B. Query Routing Strategy

```python
def route_query(user_query, estimated_size):
    """Intelligent query routing"""
    
    # 1. Check cache first
    if cached_result := cache.get(hash(user_query)):
        return cached_result
    
    # 2. Check if pre-aggregated data available
    if is_aggregatable(user_query):
        return query_aggregated_table(user_query)
    
    # 3. Use vector search for semantic queries
    if is_semantic_query(user_query):
        context = vector_store.search(user_query)
        return llm_with_context(user_query, context)
    
    # 4. For large scans, use distributed engine
    if estimated_size > THRESHOLD:
        return spark_query(user_query)
    
    # 5. Default to DuckDB for medium queries
    return duckdb_query(user_query)
```

#### C. Vector Store Integration

```
Pre-Processing:
    ├─> Generate embeddings for:
    │   ├─> Monthly summaries
    │   ├─> Category insights
    │   ├─> Regional reports
    │   └─> Product descriptions
    ↓
Store in Vector DB (Pinecone/Weaviate)
    ↓
Query Time:
    ├─> Embed user query
    ├─> Similarity search (top K)
    ├─> Retrieve relevant context
    └─> Augment LLM prompt
```

#### D. Cost Optimization Strategies

**1. Query Result Caching**
```python
# Cache frequently asked queries
cache_ttl = {
    "summary": 3600,      # 1 hour
    "category_top": 1800, # 30 minutes
    "daily_stats": 300    # 5 minutes
}
```

**2. Model Selection**
```python
# Use appropriate model for complexity
if query_complexity == "simple":
    model = "gpt-3.5-turbo"  # $0.001/1K tokens
elif query_complexity == "medium":
    model = "gpt-4o"         # $0.005/1K tokens
else:
    model = "gpt-4-turbo"    # $0.01/1K tokens
```

**3. Pre-Aggregation**
```sql
-- Maintain materialized views
CREATE MATERIALIZED VIEW daily_category_sales AS
SELECT 
    DATE_TRUNC('day', date) as day,
    category,
    SUM(amount) as revenue,
    COUNT(*) as orders
FROM sales
GROUP BY day, category;
```

## Cost Analysis

### Current Implementation (OpenAI GPT-4)

**Per Query Cost Breakdown:**

| Component | Cost | Notes |
|-----------|------|-------|
| Query Resolution | $0.03 | ~1K input + 500 output tokens |
| Synthesis | $0.05 | ~2K input + 1K output tokens |
| **Total per Q&A** | **$0.08** | Average per question |
| Summary Generation | $0.15 | Larger context |

**Monthly Cost Estimate:**
- 1,000 queries/month: ~$80
- 10,000 queries/month: ~$800
- 100,000 queries/month: ~$8,000

**Optimization Strategies:**
1. Cache common queries (80% hit rate = 80% cost savings)
2. Use GPT-3.5 for simple queries (10x cheaper)
3. Batch similar queries
4. Pre-compute summaries

### Scalable Architecture Costs (100GB data)

**Infrastructure (Cloud - AWS example):**

| Service | Spec | Monthly Cost |
|---------|------|--------------|
| EKS Cluster | 3 x t3.xlarge | $250 |
| BigQuery | 100GB + 1TB queries | $150 |
| S3 Storage | 100GB | $2.30 |
| Redis Cache | r6g.large | $120 |
| Pinecone | 1M vectors | $70 |
| Load Balancer | ALB | $20 |
| **Total Infrastructure** | | **~$612/month** |

**LLM Costs:**
- GPT-4: ~$800/month (10K queries)
- Caching saves: ~$640/month (80% hit rate)
- **Net LLM Cost**: **~$160/month**

**Total Monthly Cost:** ~$772 for 10,000 queries

## Performance Considerations

### Latency Breakdown

**Current System (Small Data):**
```
User Query
│
├─> Query Resolution: 2-3 seconds (LLM)
├─> Data Extraction: 0.1-0.5 seconds (DuckDB)
├─> Validation: <0.1 seconds
├─> Synthesis: 3-5 seconds (LLM)
│
Total: 5-9 seconds per query
```

**Optimized System:**
```
User Query
│
├─> Cache Check: <0.01 seconds (hit: 80%)
│   └─> Return cached result: ~0.01 seconds
│
├─> Cache Miss (20%)
│   ├─> Query Resolution: 1-2 seconds (caching)
│   ├─> Data Extraction: 0.2-1 seconds (indexed)
│   ├─> Validation: <0.1 seconds
│   └─> Synthesis: 2-3 seconds (streaming)
│
Average latency: 0.8-2 seconds per query
```

### Throughput

**Current:** 
- Single instance: ~10 queries/minute
- Limited by LLM API rate limits

**Scaled:**
- Multiple instances + load balancer
- Redis caching
- **Target:** 1000+ queries/minute
- Horizontal scaling as needed

### Database Performance

**DuckDB Benchmarks:**
- 1M row scan: ~100ms
- 10M row scan: ~500ms
- Aggregation (10M rows): ~300ms

**BigQuery Benchmarks:**
- 1B row scan: ~2-5 seconds
- Complex join (100M rows): ~5-10 seconds
- Cached queries: ~1 second

---

## Enterprise Features

### Query Caching (80% Cost Savings)

**File:** `backend/scalability.py` → `QueryCache`

```python
from backend.agents import MultiAgentRetailAssistant

# Enable caching
assistant = MultiAgentRetailAssistant(
    api_key="your-key",
    enable_caching=True  # ← Enable query caching
)

# Automatic cache management
# - Memory backend (local deployment)
# - Redis backend (distributed deployment)
# - 80% hit rate typical
# - Configurable TTL
```

**Benefits:**
- 80% reduction in LLM costs
- Sub-second response for cached queries
- Automatic cache invalidation
- Shared cache across instances (Redis)

### RAG & Vector Search

**File:** `backend/rag_vector_store.py`

```python
# Enable vector search
assistant = MultiAgentRetailAssistant(
    api_key="your-key",
    enable_caching=True,
    enable_rag=True  # ← Enable RAG
)

# Vector stores supported:
# - FAISS (local, fast)
# - ChromaDB (persistent)
# - Pinecone (production, scalable)
```

**How it works:**
1. Pre-compute embeddings for summaries/insights
2. Store in vector database
3. On query: retrieve top-K similar contexts
4. Augment LLM prompt with relevant context
5. Generate better, more contextual answers

### Performance Monitoring

**File:** `backend/scalability.py` → `PerformanceMonitor`

```python
# Get metrics
metrics = assistant.get_performance_metrics()

# Returns:
{
    "total_queries": 1500,
    "total_cost_usd": "$12.50",
    "avg_execution_time": "1.8s",
    "avg_cost_per_query": "$0.0083",
    "cache_hit_rate": "78.3%",
    "total_requests": 1500
}

# Set alerts
alerts = assistant.get_alerts(max_cost=50, max_latency=5)
# Returns: List of threshold violations
```

**Tracks:**
- Query count and latency
- LLM token usage and costs
- Cache hit rates
- Error rates
- Model selection distribution

### Workflow Orchestration

**File:** `backend/scalability.py` → `WorkflowOrchestrator`

```python
# Automatic retry with exponential backoff
# Fallback to cached results on failure
# Query routing based on complexity
# Cost optimization via model selection
```

**Features:**
- Retry logic (3 attempts with backoff)
- Graceful degradation
- Cost-aware model selection
- Cache-first execution

---

## Deployment Options

### Local (Current)
```bash
# Already running
python main.py
# or
streamlit run frontend/app.py
```

**Good for:**
- Development
- Testing
- Small datasets (<1GB)
- Single user

### Docker
```bash
# Build image
docker build -t retail-insights .

# Run container
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  retail-insights
```

**Good for:**
- Consistent environments
- Easy deployment
- Medium datasets (1-10GB)
- 10-100 users

### Kubernetes (Enterprise)
```bash
# Deploy cluster
kubectl apply -f k8s/deployment.yaml

# Scale horizontally
kubectl scale deployment retail-insights --replicas=10
```

**Good for:**
- Large datasets (100GB+)
- High availability
- Auto-scaling
- 100+ concurrent users

---

## Summary

This architecture provides:

✅ **Immediate Value**: Working system with sample data  
✅ **Scalability Path**: Clear roadmap to 100GB+  
✅ **Cost Efficiency**: 80% savings with caching  
✅ **Maintainability**: Clean separation of concerns  
✅ **Extensibility**: Easy to add new agents/features  
✅ **Production-Ready**: Monitoring, caching, error handling  
✅ **Enterprise Features**: RAG, distributed caching, auto-scaling  

The multi-agent design allows for:
- Parallel development of agents
- Easy testing and debugging
- Clear responsibility boundaries
- Flexible workflow modifications

**For deployment guides:** See `README.md` (Scalability section)  
**For implementation details:** See `backend/scalability.py`, `backend/rag_vector_store.py`

---

*Last Updated: December 2025*  
*Version: 2.0 - Production Ready*


