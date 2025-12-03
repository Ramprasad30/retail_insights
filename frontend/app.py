import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any
import json
import os
import sys

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import PAGE_TITLE, PAGE_ICON, LAYOUT, OPENAI_API_KEY, GOOGLE_API_KEY
from backend.agents import MultiAgentRetailAssistant
from backend.data_processor import RetailDataProcessor

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# Simple custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        color: #1E88E5;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 5px;
        border-left: 3px solid #1E88E5;
    }
    .insight-box {
        background-color: #f0f4f8;
        padding: 1rem;
        border-radius: 5px;
        border-left: 3px solid #2196F3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_assistant(api_key: str, provider: str = "OpenAI"):
    try:
        return MultiAgentRetailAssistant(api_key=api_key, provider=provider)
    except Exception as e:
        st.error(f"Error initializing assistant: {e}")
        return None


@st.cache_resource
def initialize_data_processor():
    try:
        processor = RetailDataProcessor()
        processor.load_data()
        return processor
    except Exception as e:
        st.error(f"Error initializing data processor: {e}")
        return None


def format_number(num: float, prefix: str = "") -> str:
    if num >= 1_000_000:
        return f"{prefix}{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{prefix}{num/1_000:.2f}K"
    else:
        return f"{prefix}{num:,.2f}"


def display_summary_dashboard(summary_stats: Dict[str, Any]):
    st.subheader("Overall Performance Metrics")
    
    # Amazon Sales Metrics
    amazon_stats = summary_stats.get('amazon_sales', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Orders",
            format_number(amazon_stats.get('total_orders', 0)),
            delta=None
        )
    
    with col2:
        st.metric(
            "Total Revenue",
            format_number(amazon_stats.get('total_revenue', 0), "₹"),
            delta=None
        )
    
    with col3:
        st.metric(
            "Avg Order Value",
            f"₹{amazon_stats.get('avg_order_value', 0):,.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            "Unique Categories",
            amazon_stats.get('unique_categories', 0),
            delta=None
        )
    
    st.divider()
    
    # Two column layout
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Top Categories by Revenue")
        top_categories = summary_stats.get('top_categories', [])
        if top_categories:
            df_categories = pd.DataFrame(top_categories)
            
            fig = px.bar(
                df_categories,
                x='revenue',
                y='Category',
                orientation='h',
                title='Top 5 Categories',
                labels={'revenue': 'Revenue (₹)', 'Category': 'Category'},
                color='revenue',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.dataframe(
                df_categories.style.format({
                    'revenue': '₹{:,.2f}',
                    'order_count': '{:,.0f}'
                }),
                use_container_width=True
            )
    
    with col_right:
        st.subheader("Top States by Revenue")
        top_states = summary_stats.get('top_states', [])
        if top_states:
            df_states = pd.DataFrame(top_states[:5])  # Top 5 states
            
            fig = px.bar(
                df_states,
                x='revenue',
                y='state',
                orientation='h',
                title='Top 5 States',
                labels={'revenue': 'Revenue (₹)', 'state': 'State'},
                color='revenue',
                color_continuous_scale='Greens'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.dataframe(
                df_states.style.format({
                    'revenue': '₹{:,.2f}',
                    'order_count': '{:,.0f}'
                }),
                use_container_width=True
            )
    
    st.divider()
    
    # Order Status Distribution
    st.subheader("Order Status Distribution")
    status_dist = summary_stats.get('status_distribution', [])
    if status_dist:
        df_status = pd.DataFrame(status_dist)
        
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            fig = px.pie(
                df_status,
                values='count',
                names='Status',
                title='Order Status Breakdown',
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col_table:
            st.dataframe(
                df_status.style.format({
                    'count': '{:,.0f}',
                    'percentage': '{:.2f}%'
                }),
                use_container_width=True,
                height=300
            )
    
    st.divider()
    
    # International Sales and Inventory
    col_intl, col_inv = st.columns(2)
    
    with col_intl:
        st.subheader("International Sales")
        intl_stats = summary_stats.get('international_sales', {})
        
        metrics_data = [
            ("Total Transactions", format_number(intl_stats.get('total_transactions', 0))),
            ("Total Pieces", format_number(intl_stats.get('total_pieces', 0))),
            ("Total Revenue", format_number(intl_stats.get('total_revenue', 0), "₹")),
            ("Unique Customers", format_number(intl_stats.get('unique_customers', 0)))
        ]
        
        for label, value in metrics_data:
            st.markdown(f"""
            <div class="metric-card">
                <h4 style="margin:0; color: #555;">{label}</h4>
                <h2 style="margin:0; color: #1E88E5;">{value}</h2>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")
    
    with col_inv:
        st.subheader("Inventory Status")
        inv_stats = summary_stats.get('inventory', {})
        
        metrics_data = [
            ("Total SKUs", format_number(inv_stats.get('total_skus', 0))),
            ("Total Stock", format_number(inv_stats.get('total_stock', 0))),
            ("Unique Categories", format_number(inv_stats.get('unique_categories', 0))),
            ("Unique Colors", format_number(inv_stats.get('unique_colors', 0)))
        ]
        
        for label, value in metrics_data:
            st.markdown(f"""
            <div class="metric-card">
                <h4 style="margin:0; color: #555;">{label}</h4>
                <h2 style="margin:0; color: #1E88E5;">{value}</h2>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")


def main():
    # Header
    st.title("Retail Insights Assistant")
    st.markdown("AI-powered analytics for retail data")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        # Auto-detect which API key is available
        openai_key = os.getenv("OPENAI_API_KEY", "")
        google_key = os.getenv("GOOGLE_API_KEY", "")
        
        # Default to whichever key is available
        if google_key and not openai_key:
            default_provider = 1  # Google Gemini
        else:
            default_provider = 0  # OpenAI
        
        # API Key selection
        api_provider = st.radio(
            "Select AI Provider:",
            ["OpenAI", "Google Gemini"],
            index=default_provider,
            horizontal=True
        )
        
        if api_provider == "OpenAI":
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                value=openai_key,
                help="Enter your OpenAI API key"
            )
            if not api_key:
                st.warning("Please enter your OpenAI API key to continue")
                st.info("Get your API key from: https://platform.openai.com/api-keys")
                st.stop()
        else:  # Google Gemini
            api_key = st.text_input(
                "Google API Key (Gemini)",
                type="password",
                value=google_key,
                help="Enter your Google Gemini API key"
            )
            if not api_key:
                st.warning("Please enter your Google Gemini API key to continue")
                st.info("Get your API key from: https://makersuite.google.com/app/apikey")
                st.stop()
        
        st.divider()
        
        # Mode selection
        st.subheader("Mode Selection")
        mode = st.radio(
            "Choose Mode:",
            ["Summary Mode", "Q&A Mode"],
            help="Summary: Automated performance dashboard\nQ&A: Ask specific questions"
        )
        
        st.divider()
        
        # About section
        st.subheader("About")
        st.info("""
        This application uses a multi-agent AI system to analyze retail data.
        
        **Technology:**
        - Multi-Agent System (4 agents)
        - LangGraph for orchestration
        - DuckDB for data processing
        - GPT-4 for natural language
        """)
        
        # Agent info
        with st.expander("Agent Details"):
            st.markdown("""
            **Active Agents:**
            1. Query Resolution Agent
            2. Data Extraction Agent
            3. Validation Agent
            4. Synthesis Agent
            """)
    
    # Initialize assistant
    with st.spinner("Initializing system..."):
        assistant = initialize_assistant(api_key, api_provider)
        data_processor = initialize_data_processor()
    
    if not assistant or not data_processor:
        st.error("Failed to initialize. Please check your configuration.")
        st.stop()
    
    st.success("System ready")
    
    # Main content based on mode
    if mode == "Summary Mode":
        st.header("Retail Performance Summary")
        st.info("Generate a comprehensive analysis of your retail performance data.")
        
        if st.button("Generate Summary", key="generate_summary"):
            with st.spinner("Analyzing data..."):
                try:
                    # Get summary statistics
                    summary_stats = data_processor.get_summary_statistics()
                    
                    # Display dashboard
                    display_summary_dashboard(summary_stats)
                    
                    st.divider()
                    st.subheader("AI-Generated Insights")
                    
                    # Get AI summary
                    ai_summary = assistant.get_summary()
                    
                    st.markdown(f"""
                    <div class="insight-box">
                        {ai_summary}
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Example info
        with st.expander("What's included in the summary?"):
            st.markdown("""
            The automated summary includes:
            - Overall performance trends
            - Top performing categories and regions
            - Order fulfillment status
            - Inventory health
            - Key recommendations
            """)
    
    else:  # Q&A Mode
        st.header("Ask Questions")
        st.info("Ask questions about your retail data in natural language.")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Example questions
        st.subheader("Example Questions")
        
        examples = [
            "What are the top 5 selling categories?",
            "Which state has the highest revenue?",
            "How many orders were cancelled?",
            "What is the average order value by category?",
            "Show me the distribution of order statuses",
            "Which products have low stock levels?",
        ]
        
        cols = st.columns(3)
        for idx, example in enumerate(examples):
            with cols[idx % 3]:
                if st.button(example, key=f"example_{idx}"):
                    st.session_state.example_query = example
        
        # Query input
        user_query = st.text_input(
            "Ask your question:",
            value=st.session_state.get("example_query", ""),
            placeholder="e.g., What are the top selling categories?",
            key="user_query_input"
        )
        
        # Clear example query after use
        if "example_query" in st.session_state:
            del st.session_state.example_query
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            submit_button = st.button("Ask Question", key="ask_question")
        
        with col2:
            if st.button("Clear Chat", key="clear_chat"):
                st.session_state.messages = []
                st.rerun()
        
        if submit_button and user_query:
            # Add user message to chat
            st.session_state.messages.append({
                "role": "user",
                "content": user_query
            })
            
            # Get AI response
            with st.spinner("Processing your question..."):
                try:
                    response = assistant.process_query(user_query, query_type="qa")
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                    
                    # Rerun to display updated chat
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Agent info
        with st.expander("How it works"):
            st.markdown("""
            Your question is processed by four specialized agents:
            
            1. **Query Resolution** - Converts your question to SQL
            2. **Data Extraction** - Runs the query and gets data
            3. **Validation** - Checks the results for quality
            4. **Synthesis** - Generates a readable answer
            
            This multi-agent approach ensures accurate and insightful responses.
            """)


if __name__ == "__main__":
    main()

