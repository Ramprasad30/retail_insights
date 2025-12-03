import json
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
import operator
import logging
import time

from .data_processor import RetailDataProcessor
from .config import OPENAI_MODEL, GEMINI_MODEL, TEMPERATURE, OPENAI_API_KEY, GOOGLE_API_KEY

# Import scalability components
try:
    from .scalability import WorkflowOrchestrator, QueryCache, PerformanceMonitor, QueryOptimizer
    from .rag_vector_store import RAGFactory, RetailKnowledgeBaseBuilder
    SCALABILITY_ENABLED = True
except ImportError:
    SCALABILITY_ENABLED = False
    logging.warning("Scalability components not available - running in basic mode")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_query: str
    query_type: str  # 'summary' or 'qa'
    sql_query: str
    data_result: Any
    validation_status: str
    final_response: str
    schema_info: Dict[str, List[str]]
    summary_stats: Dict[str, Any]
    iteration: int


class MultiAgentRetailAssistant:
    
    def __init__(self, api_key: str = None, provider: str = "OpenAI", enable_caching: bool = True, enable_rag: bool = False):
        self.provider = provider
        self.api_key = api_key
        
        if not self.api_key:
            if provider == "OpenAI":
                self.api_key = OPENAI_API_KEY
            else:
                self.api_key = GOOGLE_API_KEY
                
        if not self.api_key:
            raise ValueError(f"{provider} API key is required")
        
        # Initialize LLMs - one for summary (long), one for Q&A (short)
        if provider == "Google Gemini":
            self.llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                temperature=TEMPERATURE,
                google_api_key=self.api_key
            )
            self.llm_short = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                temperature=0.3,
                google_api_key=self.api_key,
                max_output_tokens=200
            )
        else:  # OpenAI
            self.llm = ChatOpenAI(
                model=OPENAI_MODEL,
                temperature=TEMPERATURE,
                api_key=self.api_key
            )
            self.llm_short = ChatOpenAI(
                model=OPENAI_MODEL,
                temperature=0.3,
                api_key=self.api_key,
                max_tokens=200
            )
        
        self.data_processor = RetailDataProcessor()
        self.data_processor.load_data()
        
        # Initialize scalability components if enabled
        self.orchestrator = None
        self.performance_monitor = None
        self.rag_retriever = None
        
        if SCALABILITY_ENABLED:
            if enable_caching:
                try:
                    cache = QueryCache(backend="memory")  # Can be upgraded to Redis
                    self.orchestrator = WorkflowOrchestrator(cache)
                    logger.info("✓ Query caching enabled")
                except Exception as e:
                    logger.warning(f"Cache initialization failed: {e}")
            
            # Initialize performance monitoring
            try:
                self.performance_monitor = PerformanceMonitor()
                logger.info("✓ Performance monitoring enabled")
            except Exception as e:
                logger.warning(f"Performance monitor initialization failed: {e}")
            
            # Initialize RAG if requested
            if enable_rag:
                try:
                    self.rag_retriever = RAGFactory.create_retriever(store_type="chroma")
                    # Build knowledge base from summary statistics
                    summary_stats = self.data_processor.get_summary_statistics()
                    kb_items = RetailKnowledgeBaseBuilder.build_from_summary_stats(summary_stats)
                    self.rag_retriever.index_knowledge_base(kb_items)
                    logger.info("✓ RAG (vector store) enabled with knowledge base")
                except Exception as e:
                    logger.warning(f"RAG initialization failed: {e}")
        
        # Build the agent graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # Add nodes (agents)
        workflow.add_node("query_resolution", self.query_resolution_agent)
        workflow.add_node("data_extraction", self.data_extraction_agent)
        workflow.add_node("validation", self.validation_agent)
        workflow.add_node("synthesis", self.synthesis_agent)
        
        # Define edges (workflow)
        workflow.set_entry_point("query_resolution")
        workflow.add_edge("query_resolution", "data_extraction")
        workflow.add_edge("data_extraction", "validation")
        workflow.add_edge("validation", "synthesis")
        workflow.add_edge("synthesis", END)
        
        return workflow.compile()
    
    def query_resolution_agent(self, state: AgentState) -> AgentState:
        # Convert natural language to SQL query
        logger.info("Query Resolution Agent: analyzing user query")
        
        user_query = state.get("user_query", "")
        schema_info = self.data_processor.get_schema_info()
        
        # Create prompt for query understanding
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an analytics Q&A engine for a retail analytics system.

Available Tables and Columns:
{schema_info}

CRITICAL INSTRUCTIONS:
-----------------------
Step 1: CLASSIFY QUESTION
-----------------------
Identify:
- Intent category: Ranking / Aggregation / Distribution / Comparison / KPI / Boolean
- Expected output type: list / dict / float / int / string / boolean
- Query type: "summary" (comprehensive overview) or "qa" (specific question)
- Requested count: Extract any number mentioned (top 3, top 5, top 10, etc.)

Rules:
- "top N", "highest", "lowest", "best", "worst" → Ranking → list
- "average", "sum", "count", "total", "min/max" → Aggregation → int/float
- "distribution", "breakdown", "status" → Distribution → dict/list
- "compare", "trend" → Comparison → boolean or numeric
- "What is the...?" → KPI → int/float/string
- Yes/No questions → boolean

IMPORTANT: Extract the specific number if user asks for "top 3", "top 6", "top 10", etc.
           Default to 5 only if no number is specified.

-----------------------
Step 2: SQL GENERATION
-----------------------
Generate SQL using ONLY these rules:
1. The 'Amount' column is ALREADY NUMERIC - use it directly, NO TRIM, NO CAST needed
2. For aggregations on Amount: SUM(Amount), AVG(Amount), MAX(Amount) - that's it!
3. For other text columns that might have numbers: use TRY_CAST(column AS DOUBLE)
4. Use proper NULL checks: WHERE column IS NOT NULL
5. For rankings: always ORDER BY metric DESC and use LIMIT N (where N is the user's requested count)
6. For distributions: use GROUP BY with COUNT(*) or SUM(Amount)
7. EXTRACT the count from user query: "top 3" → LIMIT 3, "top 10" → LIMIT 10, no number → LIMIT 5

Column Type Reference:
- Amount: NUMERIC (ready to use)
- Qty: TEXT (use TRY_CAST if needed)
- Category, Status, ship-state: TEXT (use as-is)
- Date: TEXT (use as-is for grouping)

-----------------------
Step 3: RESPOND WITH JSON
-----------------------
Return ONLY this JSON format:
{{
    "intent": "<Ranking|Aggregation|Distribution|Comparison|KPI|Boolean>",
    "query_type": "<summary|qa>",
    "expected_output_type": "<string|int|float|list|dict|boolean>",
    "reasoning": "Brief explanation",
    "sql_query": "<valid_duckdb_sql>",
    "tables_used": ["table_names"]
}}

EXAMPLES:

Q: "What are the top 5 selling categories?"
{{
    "intent": "Ranking",
    "query_type": "qa",
    "expected_output_type": "list",
    "reasoning": "User wants ranked list of top 5 categories by sales",
    "sql_query": "SELECT Category, SUM(Amount) AS TotalSales FROM amazon_sales WHERE Category IS NOT NULL GROUP BY Category ORDER BY TotalSales DESC LIMIT 5",
    "tables_used": ["amazon_sales"]
}}

Q: "What are the top 10 selling categories?"
{{
    "intent": "Ranking",
    "query_type": "qa",
    "expected_output_type": "list",
    "reasoning": "User wants ranked list of top 10 categories by sales",
    "sql_query": "SELECT Category, SUM(Amount) AS TotalSales FROM amazon_sales WHERE Category IS NOT NULL GROUP BY Category ORDER BY TotalSales DESC LIMIT 10",
    "tables_used": ["amazon_sales"]
}}

Q: "Which state has the highest revenue?"
{{
    "intent": "Ranking",
    "query_type": "qa",
    "expected_output_type": "string",
    "reasoning": "User wants the single state with max revenue",
    "sql_query": "SELECT \\"ship-state\\", SUM(Amount) AS total_revenue FROM amazon_sales WHERE \\"ship-state\\" IS NOT NULL GROUP BY \\"ship-state\\" ORDER BY total_revenue DESC LIMIT 1",
    "tables_used": ["amazon_sales"]
}}

Q: "What is the average order value?"
{{
    "intent": "Aggregation",
    "query_type": "qa",
    "expected_output_type": "float",
    "reasoning": "User wants average of Amount column",
    "sql_query": "SELECT AVG(Amount) AS avg_order_value FROM amazon_sales WHERE Amount IS NOT NULL",
    "tables_used": ["amazon_sales"]
}}

Remember: Amount is NUMERIC - never use TRIM() on it!
"""),
            ("user", "{user_query}")
        ])
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "schema_info": json.dumps(schema_info, indent=2),
            "user_query": user_query
        })
        
        # Parse the response
        try:
            # Try to extract JSON from the response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # DO NOT overwrite query_type - respect the user's mode selection from UI
            # state["query_type"] = result.get("query_type", "qa")  # REMOVED - was causing bug!
            state["sql_query"] = result.get("sql_query", "")
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Query Analysis: {result.get('reasoning', '')}")
            ]
            
            logger.info(f"Query Type (from UI): {state['query_type']}")
            logger.info(f"SQL Query: {state['sql_query']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing query resolution response: {e}")
            state["query_type"] = "qa"
            state["sql_query"] = ""
            state["messages"] = state.get("messages", []) + [
                AIMessage(content="I need help understanding your query. Could you rephrase it?")
            ]
        
        state["schema_info"] = schema_info
        state["iteration"] = state.get("iteration", 0) + 1
        
        return state
    
    def data_extraction_agent(self, state: AgentState) -> AgentState:
        logger.info("Data Extraction Agent: executing query")
        
        query_type = state.get("query_type", "qa")
        sql_query = state.get("sql_query", "")
        
        # For summary mode, use pre-loaded summary stats
        if query_type == "summary":
            logger.info("Summary mode - using pre-loaded stats")
            if state.get("summary_stats"):
                state["data_result"] = state["summary_stats"]
            else:
                state["data_result"] = self.data_processor.get_summary_statistics()
            state["validation_status"] = "PASSED"
            return state
        
        # For Q&A mode without SQL, use summary stats but mark for concise response
        if not sql_query:
            logger.info("Q&A mode without SQL - using summary stats for answer")
            state["data_result"] = self.data_processor.get_summary_statistics()
            state["validation_status"] = "PASSED"
            return state
        
        try:
            # Execute the query
            result_df = self.data_processor.execute_query(sql_query)
            
            # Convert to dictionary for easier handling
            if len(result_df) > 0:
                # Limit results to prevent overwhelming the LLM
                if len(result_df) > 100:
                    logger.info(f"Limiting results from {len(result_df)} to 100 rows")
                    result_df = result_df.head(100)
                
                state["data_result"] = {
                    "data": result_df.to_dict('records'),
                    "row_count": len(result_df),
                    "columns": list(result_df.columns)
                }
                
                logger.info(f"Retrieved {len(result_df)} rows")
            else:
                state["data_result"] = {
                    "data": [],
                    "row_count": 0,
                    "columns": []
                }
                logger.info("Query returned no results")
            
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Data extracted: {len(result_df)} rows retrieved")
            ]
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.info("SQL failed, falling back to summary statistics")
            
            # For Q&A mode, try to use summary stats as fallback
            if state.get("query_type") == "qa":
                try:
                    summary_stats = self.data_processor.get_summary_statistics()
                    state["data_result"] = summary_stats
                    state["validation_status"] = "PASSED"
                    state["messages"] = state.get("messages", []) + [
                        AIMessage(content="Using summary data to answer your question")
                    ]
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    state["data_result"] = {
                        "error": f"Query error: {str(e)}",
                        "data": [],
                        "row_count": 0
                    }
                    state["messages"] = state.get("messages", []) + [
                        AIMessage(content=f"I encountered an error: {str(e)[:100]}")
                    ]
            else:
                state["data_result"] = {
                    "error": str(e),
                    "data": [],
                    "row_count": 0
                }
                state["messages"] = state.get("messages", []) + [
                    AIMessage(content=f"Error extracting data: {str(e)}")
                ]
        
        return state
    
    def validation_agent(self, state: AgentState) -> AgentState:
        logger.info("Validation Agent: checking data quality")
        
        # Skip validation if already passed (summary mode)
        if state.get("validation_status") == "PASSED":
            logger.info("Validation already passed, skipping")
            return state
        
        data_result = state.get("data_result", {})
        validation_checks = []
        
        # Check if there's an error
        if "error" in data_result:
            validation_checks.append({
                "check": "Error Detection",
                "status": "FAILED",
                "message": f"Query execution error: {data_result['error']}"
            })
            state["validation_status"] = "FAILED"
        else:
            # Check if data was returned
            row_count = data_result.get("row_count", 0)
            
            if row_count == 0:
                validation_checks.append({
                    "check": "Data Availability",
                    "status": "WARNING",
                    "message": "Query returned no results"
                })
                state["validation_status"] = "WARNING"
            else:
                validation_checks.append({
                    "check": "Data Availability",
                    "status": "PASSED",
                    "message": f"{row_count} rows retrieved successfully"
                })
                
                # Check data structure
                if "columns" in data_result and len(data_result["columns"]) > 0:
                    validation_checks.append({
                        "check": "Data Structure",
                        "status": "PASSED",
                        "message": f"{len(data_result['columns'])} columns present"
                    })
                
                state["validation_status"] = "PASSED"
        
        # Log validation results
        for check in validation_checks:
            logger.info(f"  {check['check']}: {check['status']} - {check['message']}")
        
        state["messages"] = state.get("messages", []) + [
            AIMessage(content=f"Validation: {state['validation_status']}")
        ]
        
        return state
    
    def _generate_direct_answer(self, query: str, data: dict) -> str:
        """Generate direct answer from data without LLM for common questions"""
        if not isinstance(data, dict):
            logger.warning(f"Data is not a dict: {type(data)}")
            return None
            
        q = query.lower()
        logger.info(f"Checking direct answer for: {q}")
        
        # Check if this is SQL query result data (has 'data', 'row_count', 'columns' keys)
        if 'data' in data and 'row_count' in data and 'columns' in data:
            logger.info(f"Processing SQL result with {data['row_count']} rows")
            rows = data['data']
            row_count = data['row_count']
            columns = data['columns']
            
            if row_count == 0:
                return "No matching data found for your query."
            
            # Format the SQL results based on what was asked
            # Top categories
            if ('categor' in q or 'selling' in q) and any(w in q for w in ['top', 'best', 'highest', '5', 'five']):
                if rows and len(rows) > 0:
                    # Dynamically show the number of results we have
                    count = min(len(rows), row_count)
                    lines = [f"**Top Selling Categories:**"]
                    for i, row in enumerate(rows, 1):
                        cat = row.get('Category', row.get('category', '?'))
                        # Check multiple possible column names for revenue
                        rev = (row.get('TotalSales') or row.get('total_sales') or 
                               row.get('revenue') or row.get('Amount') or 0)
                        lines.append(f"{i}. {cat} - ₹{rev:,.0f}")
                    return "\n".join(lines)
            
            # State revenue question
            if 'state' in q and any(w in q for w in ['highest', 'most', 'top', 'best']) and 'revenue' in q:
                if rows and len(rows) > 0:
                    row = rows[0]
                    state = row.get('ship-state', row.get('state', '?'))
                    # Check multiple possible column names for revenue
                    revenue = (row.get('total_revenue') or row.get('TotalRevenue') or 
                               row.get('revenue') or row.get('Amount') or 0)
                    return f"**{state}** has the highest revenue at ₹{revenue:,.0f}."
            
            # Low stock / inventory questions
            if any(w in q for w in ['stock', 'inventory', 'low']) and row_count > 0:
                lines = [f"**Found {row_count} products with low stock:**"]
                for i, row in enumerate(rows[:10], 1):  # Show first 10
                    sku = row.get('SKU Code', row.get('sku', '?'))
                    design = row.get('Design No.', row.get('design', ''))
                    cat = row.get('Category', row.get('category', '?'))
                    stock = row.get('Stock', row.get('stock', 0))
                    lines.append(f"{i}. {cat} - {design or sku} (Stock: {stock})")
                if row_count > 10:
                    lines.append(f"...and {row_count - 10} more products")
                return "\n".join(lines)
            
            # Generic result formatting for other queries
            if row_count == 1 and len(columns) <= 2:
                # Simple single-value answer
                row = rows[0]
                if len(columns) == 1:
                    val = row.get(columns[0], '?')
                    return f"**{val}**"
                else:
                    # Two columns, format as key-value
                    k = row.get(columns[0], '?')
                    v = row.get(columns[1], '?')
                    if isinstance(v, (int, float)):
                        return f"**{k}:** ₹{v:,.0f}" if v > 1000 else f"**{k}:** {v:,.2f}"
                    return f"**{k}:** {v}"
            
            # For multiple rows with numeric data, format as a list
            if row_count > 1 and len(columns) == 2:
                # Check if second column is numeric
                first_val = rows[0].get(columns[1], 0)
                if isinstance(first_val, (int, float)):
                    lines = [f"**{columns[0]} by {columns[1]}:**"]
                    for i, row in enumerate(rows[:10], 1):
                        k = row.get(columns[0], '?')
                        v = row.get(columns[1], 0)
                        if v > 1000:  # Likely currency
                            lines.append(f"{i}. {k} - ₹{v:,.0f}")
                        elif v > 1:  # Regular number
                            lines.append(f"{i}. {k} - {v:,.2f}")
                        else:  # Small decimal
                            lines.append(f"{i}. {k} - {v:.2f}")
                    if row_count > 10:
                        lines.append(f"...and {row_count - 10} more")
                    return "\n".join(lines)
            
            # For multiple rows, let LLM handle formatting
            return None
        
        # OLD LOGIC: For summary statistics format (fallback)
        # Top categories - match various phrasings
        if ('categor' in q or 'product' in q or 'selling' in q) and any(w in q for w in ['top', 'best', 'highest', '5', 'five']):
            cats = data.get('top_categories', [])
            if cats:
                # Extract requested count from query, default to 5
                import re
                count_match = re.search(r'top\s+(\d+)|(\d+)\s+top', q.lower())
                requested_count = int(count_match.group(1) or count_match.group(2)) if count_match else 5
                
                cats = cats[:requested_count]  # Limit to requested count
                lines = [f"**Top {requested_count} Categories by Revenue:**"]
                for i, c in enumerate(cats, 1):
                    lines.append(f"{i}. {c.get('Category', '?')} - ₹{c.get('revenue', 0):,.0f} ({c.get('order_count', 0):,} orders)")
                return "\n".join(lines)
        
        # Top states
        if any(w in q for w in ['top', 'best', 'highest']) and 'state' in q:
            states = data.get('top_states', [])
            if states:
                # Extract requested count from query, default to 5
                import re
                count_match = re.search(r'top\s+(\d+)|(\d+)\s+top', q.lower())
                requested_count = int(count_match.group(1) or count_match.group(2)) if count_match else 5
                
                states = states[:requested_count]
                lines = [f"**Top {requested_count} States by Revenue:**"]
                for i, s in enumerate(states, 1):
                    lines.append(f"{i}. {s.get('state', '?')} - ₹{s.get('revenue', 0):,.0f} ({s.get('order_count', 0):,} orders)")
                return "\n".join(lines)
        
        # Which state highest
        if 'which state' in q and any(w in q for w in ['highest', 'most', 'top']):
            states = data.get('top_states', [])
            if states:
                s = states[0]
                return f"**{s.get('state', '?')}** has the highest revenue at ₹{s.get('revenue', 0):,.0f} from {s.get('order_count', 0):,} orders."
        
        # Cancelled orders
        if 'cancel' in q:
            status = data.get('status_distribution', [])
            for s in status:
                if 'cancel' in s.get('Status', '').lower():
                    return f"**{s.get('count', 0):,} orders were cancelled** ({s.get('percentage', 0)}% of total)."
        
        # Total revenue
        if 'total revenue' in q or 'total sales' in q:
            amazon = data.get('amazon_sales', {})
            return f"**Total Revenue:** ₹{amazon.get('total_revenue', 0):,.0f} from {amazon.get('total_orders', 0):,} orders."
        
        # Average order value
        if 'average' in q and 'order' in q:
            amazon = data.get('amazon_sales', {})
            return f"**Average Order Value:** ₹{amazon.get('avg_order_value', 0):,.2f}"
        
        # How many orders
        if 'how many' in q and 'order' in q:
            amazon = data.get('amazon_sales', {})
            return f"**Total Orders:** {amazon.get('total_orders', 0):,}"
        
        # Status distribution
        if 'status' in q and 'distribution' in q:
            status = data.get('status_distribution', [])[:5]
            if status:
                lines = ["**Order Status Distribution:**"]
                for s in status:
                    lines.append(f"• {s.get('Status', '?')} - {s.get('count', 0):,} ({s.get('percentage', 0)}%)")
                return "\n".join(lines)
        
        return None  # Let LLM handle complex questions
    
    def _format_data_concisely(self, query: str, full_data: dict) -> str:
        """Format relevant data concisely for LLM context"""
        query_lower = query.lower()
        parts = []
        
        # Add relevant sections based on query keywords
        if 'amazon_sales' in full_data:
            s = full_data['amazon_sales']
            parts.append(f"Sales: {s.get('total_orders',0):,} orders, ₹{s.get('total_revenue',0):,.0f} revenue, ₹{s.get('avg_order_value',0):,.0f} avg order")
        
        if 'top_categories' in full_data and any(w in query_lower for w in ['categor', 'product', 'selling', 'top']):
            cats = full_data['top_categories'][:5]
            cat_str = ", ".join([f"{c.get('Category','?')}: ₹{c.get('revenue',0):,.0f}" for c in cats])
            parts.append(f"Top Categories: {cat_str}")
        
        if 'top_states' in full_data and any(w in query_lower for w in ['state', 'region', 'where', 'location']):
            states = full_data['top_states'][:5]
            state_str = ", ".join([f"{s.get('state','?')}: ₹{s.get('revenue',0):,.0f}" for s in states])
            parts.append(f"Top States: {state_str}")
        
        if 'status_distribution' in full_data and any(w in query_lower for w in ['status', 'cancel', 'deliver', 'ship']):
            statuses = full_data['status_distribution']
            status_str = ", ".join([f"{s.get('Status','?')}: {s.get('count',0):,} ({s.get('percentage',0)}%)" for s in statuses[:5]])
            parts.append(f"Order Status: {status_str}")
        
        if 'inventory' in full_data and any(w in query_lower for w in ['inventory', 'stock', 'sku']):
            inv = full_data['inventory']
            parts.append(f"Inventory: {inv.get('total_skus',0):,} SKUs, {inv.get('total_stock',0):,} units")
        
        # If no specific match, include basic sales info
        if len(parts) <= 1:
            if 'top_categories' in full_data:
                cats = full_data['top_categories'][:5]
                cat_str = ", ".join([f"{c.get('Category','?')}: ₹{c.get('revenue',0):,.0f}" for c in cats])
                parts.append(f"Top Categories: {cat_str}")
            if 'top_states' in full_data:
                states = full_data['top_states'][:3]
                state_str = ", ".join([f"{s.get('state','?')}: ₹{s.get('revenue',0):,.0f}" for s in states])
                parts.append(f"Top States: {state_str}")
        
        return " | ".join(parts)
    
    def _filter_relevant_data(self, query: str, full_data: dict) -> dict:
        """Filter data to only include parts relevant to the user's question"""
        query_lower = query.lower()
        filtered = {}
        
        if any(word in query_lower for word in ['categor', 'product', 'selling', 'top 5', 'top five', 'best']):
            if 'top_categories' in full_data:
                filtered['top_categories'] = full_data['top_categories']
        
        if any(word in query_lower for word in ['state', 'region', 'location', 'where', 'geographic']):
            if 'top_states' in full_data:
                filtered['top_states'] = full_data['top_states']
        
        if any(word in query_lower for word in ['status', 'cancel', 'deliver', 'ship', 'return']):
            if 'status_distribution' in full_data:
                filtered['status_distribution'] = full_data['status_distribution']
        
        if any(word in query_lower for word in ['revenue', 'sales', 'total', 'money', 'how much']):
            if 'amazon_sales' in full_data:
                filtered['amazon_sales'] = full_data['amazon_sales']
        
        if not filtered:
            filtered = {'amazon_sales': full_data.get('amazon_sales', {})}
        
        return filtered
    
    def synthesis_agent(self, state: AgentState) -> AgentState:
        logger.info("Synthesis Agent: generating response")
        
        user_query = state.get("user_query", "")
        data_result = state.get("data_result", {})
        validation_status = state.get("validation_status", "UNKNOWN")
        query_type = state.get("query_type", "qa")
        
        # Create synthesis prompt
        if validation_status == "FAILED":
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful retail analytics assistant.
The data query encountered an error. Provide a helpful response to the user explaining what went wrong
and suggest how they might rephrase their question."""),
                ("user", """
User Query: {user_query}

Error Information: {error_info}

Provide a helpful, conversational response.""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "user_query": user_query,
                "error_info": data_result.get("error", "Unknown error")
            })
            
        elif validation_status == "WARNING":
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful retail analytics assistant.
The query executed successfully but returned no results. Help the user understand why and suggest alternatives."""),
                ("user", """
User Query: {user_query}

The query returned no results. Provide a helpful response explaining possible reasons
and suggest alternative queries.""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "user_query": user_query
            })
            
        else:
            # CLEAR SEPARATION: Summary vs Q&A
            logger.info(f"Query type: {query_type}")
            
            if query_type == "summary":
                # SUMMARY MODE: Full executive report
                logger.info("=== SUMMARY MODE ===")
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert retail analytics consultant.
Generate a comprehensive, executive-level summary of the retail performance data provided.

Guidelines:
- Start with key highlights and overall trends
- Include specific numbers and percentages
- Identify top performers and areas of concern
- Use business language, not technical jargon
- Structure your response with clear sections
- Be concise but insightful"""),
                    ("user", """
Data Summary:
{data_summary}

Generate a professional business summary of the retail performance.""")
                ])
                
                chain = prompt | self.llm
                response = chain.invoke({
                    "user_query": user_query,
                    "data_summary": json.dumps(data_result, indent=2)
                })
            else:
                # Q&A MODE: Short direct answers
                logger.info("=== Q&A MODE ===")
                logger.info(f"User query: {user_query}")
                logger.info(f"Data keys: {data_result.keys() if isinstance(data_result, dict) else 'not a dict'}")
                
                # Try direct answer first (no LLM)
                direct_answer = self._generate_direct_answer(user_query, data_result)
                logger.info(f"Direct answer result: {direct_answer[:100] if direct_answer else 'None'}")
                
                if direct_answer:
                    state["final_response"] = direct_answer
                    state["messages"] = state.get("messages", []) + [AIMessage(content=direct_answer)]
                    logger.info("Returning direct answer")
                    return state
                
                # Fallback to LLM with better context
                logger.info("Falling back to LLM")
                
                # If we have SQL query results, format them nicely for the LLM
                if 'data' in data_result and data_result.get('row_count', 0) > 0:
                    rows = data_result['data']
                    row_count = data_result['row_count']
                    
                    # Create a concise data summary for LLM
                    data_summary = f"Query returned {row_count} results:\n"
                    for i, row in enumerate(rows[:20], 1):  # Show first 20 rows
                        data_summary += f"{i}. {row}\n"
                    if row_count > 20:
                        data_summary += f"...and {row_count - 20} more rows"
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", """You are a retail analytics assistant. Answer the question based ONLY on the data provided.
                        
Guidelines:
- Be direct and concise (2-3 sentences max)
- Include specific numbers from the data
- Format numbers with proper units (₹ for currency, commas for thousands)
- If showing a list, format it clearly
- Don't add analysis unless asked"""),
                        ("user", "Question: {user_query}\n\nData:\n{data_summary}\n\nProvide a direct answer:")
                    ])
                    
                    chain = prompt | self.llm_short
                    response = chain.invoke({
                        "user_query": user_query,
                        "data_summary": data_summary
                    })
                else:
                    # No results or summary stats
                    concise_data = self._format_data_concisely(user_query, data_result)
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "Answer in ONE sentence. No analysis."),
                        ("user", "{user_query}\n{data}")
                    ])
                    chain = prompt | self.llm_short
                    response = chain.invoke({"user_query": user_query, "data": concise_data})
        
        final_response = response.content
        state["final_response"] = final_response
        state["messages"] = state.get("messages", []) + [
            AIMessage(content=final_response)
        ]
        
        logger.info("Synthesis complete")
        
        return state
    
    def process_query(self, user_query: str, query_type: str = "qa") -> str:
        logger.info(f"Processing query: {user_query}")
        start_time = time.time()
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "user_query": user_query,
            "query_type": query_type,
            "sql_query": "",
            "data_result": {},
            "validation_status": "",
            "final_response": "",
            "schema_info": {},
            "summary_stats": {},
            "iteration": 0
        }
        
        # If it's a summary request, get summary statistics directly
        if query_type == "summary":
            logger.info("Summary mode - retrieving comprehensive statistics")
            initial_state["summary_stats"] = self.data_processor.get_summary_statistics()
            initial_state["data_result"] = initial_state["summary_stats"]
        
        # Run the agent graph
        final_state = self.graph.invoke(initial_state)
        
        execution_time = time.time() - start_time
        
        # Log performance metrics if monitor is available
        if self.performance_monitor:
            # Estimate token usage (rough approximation)
            estimated_tokens = len(user_query.split()) * 1.3 + len(final_state.get("final_response", "").split()) * 1.3
            self.performance_monitor.log_query(
                query=user_query,
                execution_time=execution_time,
                tokens_used=int(estimated_tokens),
                model=GEMINI_MODEL if self.provider == "Google Gemini" else OPENAI_MODEL
            )
        
        return final_state.get("final_response", "I apologize, but I couldn't generate a response.")
    
    def get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """Get performance and cost metrics"""
        if not self.performance_monitor:
            return None
        
        metrics = self.performance_monitor.get_cost_summary()
        
        # Add cache metrics if available
        if self.orchestrator:
            cache_metrics = self.orchestrator.get_metrics()
            metrics.update(cache_metrics)
        
        return metrics
    
    def get_alerts(self, max_cost: float = 100.0, max_latency: float = 10.0) -> List[str]:
        """Check for performance alerts"""
        if not self.performance_monitor:
            return []
        return self.performance_monitor.check_alert_thresholds(max_cost, max_latency)
    
    def get_summary(self) -> str:
        return self.process_query(
            "Generate a comprehensive summary of retail performance across all datasets",
            query_type="summary"
        )
    
    def close(self):
        if self.data_processor:
            self.data_processor.close()