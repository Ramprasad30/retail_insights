"""
Retail Insights Pro - Best-in-Market Analytics Dashboard
=========================================================
A comprehensive, production-grade retail analytics platform
featuring AI-powered insights, geographic visualization,
time intelligence, and seamless data onboarding.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Optional
import json
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO, StringIO
import base64

# Path setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import PAGE_TITLE, PAGE_ICON, LAYOUT, OPENAI_API_KEY, GOOGLE_API_KEY
from backend.agents import MultiAgentRetailAssistant
from backend.data_processor import RetailDataProcessor

# Try to import data intake agent
try:
    from backend.data_intake_agent import UniversalDataIntakeAgent
    INTAKE_AGENT_AVAILABLE = True
except ImportError:
    INTAKE_AGENT_AVAILABLE = False

logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Retail Insights Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PREMIUM DARK THEME - MARKET-LEADING DESIGN
# ============================================================================

st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    /* Root Variables */
    :root {
        --primary: #667eea;
        --primary-dark: #5a67d8;
        --secondary: #764ba2;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #3b82f6;
        --bg-dark: #0f0f1a;
        --bg-card: #1a1a2e;
        --bg-card-hover: #252542;
        --text-primary: #ffffff;
        --text-secondary: rgba(255,255,255,0.7);
        --text-muted: rgba(255,255,255,0.5);
        --border: rgba(255,255,255,0.1);
        --gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Global */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg-dark);
    }
    
    /* Hide Streamlit Elements */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Main Header */
    .main-header {
        background: var(--gradient);
        padding: 1.75rem 2rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
        animation: shimmer 3s infinite;
    }
    
    @keyframes shimmer {
        0%, 100% { transform: rotate(0deg); }
        50% { transform: rotate(180deg); }
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.25rem;
        font-weight: 800;
        margin: 0;
        position: relative;
        z-index: 1;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
        position: relative;
        z-index: 1;
    }
    
    /* Navigation Tabs */
    .nav-container {
        display: flex;
        gap: 0.5rem;
        background: var(--bg-card);
        padding: 0.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid var(--border);
        overflow-x: auto;
    }
    
    .nav-tab {
        padding: 0.75rem 1.25rem;
        border-radius: 12px;
        color: var(--text-secondary);
        font-weight: 500;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.3s ease;
        white-space: nowrap;
        border: none;
        background: transparent;
    }
    
    .nav-tab:hover {
        background: rgba(255,255,255,0.05);
        color: var(--text-primary);
    }
    
    .nav-tab.active {
        background: var(--gradient);
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .kpi-card {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 1.25rem;
        border: 1px solid var(--border);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: var(--gradient);
        border-radius: 4px 0 0 4px;
    }
    
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.15);
        border-color: rgba(102, 126, 234, 0.3);
    }
    
    .kpi-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.2;
    }
    
    .kpi-label {
        color: var(--text-secondary);
        font-size: 0.85rem;
        margin-top: 0.25rem;
        font-weight: 500;
    }
    
    .kpi-change {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.8rem;
        margin-top: 0.5rem;
        padding: 0.2rem 0.5rem;
        border-radius: 20px;
        font-weight: 600;
    }
    
    .kpi-change.up {
        background: rgba(16, 185, 129, 0.15);
        color: var(--success);
    }
    
    .kpi-change.down {
        background: rgba(239, 68, 68, 0.15);
        color: var(--danger);
    }
    
    /* Chart Container */
    .chart-card {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 1.25rem;
        border: 1px solid var(--border);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .chart-card:hover {
        border-color: rgba(102, 126, 234, 0.2);
    }
    
    .chart-title {
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Section Header */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border);
    }
    
    .section-header h2 {
        color: var(--text-primary);
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0;
    }
    
    /* Alert Boxes */
    .alert {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .alert.success {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: var(--success);
    }
    
    .alert.warning {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.2);
        color: var(--warning);
    }
    
    .alert.danger {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: var(--danger);
    }
    
    .alert.info {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.2);
        color: var(--info);
    }
    
    /* Insight Card */
    .insight-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    
    .insight-card p {
        color: var(--text-secondary);
        margin: 0;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    
    .insight-card strong {
        color: var(--primary);
    }
    
    /* Upload Zone */
    .upload-zone {
        border: 2px dashed rgba(102, 126, 234, 0.4);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        background: rgba(102, 126, 234, 0.05);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .upload-zone:hover {
        border-color: var(--primary);
        background: rgba(102, 126, 234, 0.1);
    }
    
    .upload-zone .icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .upload-zone h3 {
        color: var(--text-primary);
        font-size: 1.25rem;
        margin: 0 0 0.5rem 0;
    }
    
    .upload-zone p {
        color: var(--text-secondary);
        margin: 0;
        font-size: 0.9rem;
    }
    
    /* Data Preview Table */
    .data-preview {
        background: var(--bg-card);
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    
    /* Metric Mini */
    .metric-mini {
        background: rgba(255,255,255,0.03);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid var(--border);
    }
    
    .metric-mini .value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        font-family: 'JetBrains Mono', monospace;
    }
    
    .metric-mini .label {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Chat Messages */
    .chat-msg {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.75rem;
    }
    
    .chat-msg.user {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
        border: 1px solid rgba(102, 126, 234, 0.2);
        margin-left: 2rem;
    }
    
    .chat-msg.assistant {
        background: var(--bg-card);
        border: 1px solid var(--border);
        margin-right: 2rem;
    }
    
    .chat-msg .role {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--primary);
        margin-bottom: 0.5rem;
    }
    
    .chat-msg .content {
        color: var(--text-secondary);
        line-height: 1.6;
    }
    
    /* Quick Action Buttons */
    .quick-btn {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 10px;
        padding: 0.6rem 1rem;
        color: var(--text-secondary);
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
        width: 100%;
    }
    
    .quick-btn:hover {
        background: rgba(102, 126, 234, 0.2);
        color: var(--text-primary);
        transform: translateX(4px);
    }
    
    /* Export Buttons */
    .export-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.25rem;
        border-radius: 10px;
        font-weight: 500;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s ease;
        border: none;
    }
    
    .export-btn.primary {
        background: var(--gradient);
        color: white;
    }
    
    .export-btn.secondary {
        background: rgba(255,255,255,0.05);
        color: var(--text-secondary);
        border: 1px solid var(--border);
    }
    
    .export-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Progress Bar */
    .progress-bar-container {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        height: 8px;
        overflow: hidden;
    }
    
    .progress-bar-fill {
        height: 100%;
        border-radius: 10px;
        background: var(--gradient);
        transition: width 0.5s ease;
    }
    
    /* Gauge Display */
    .gauge-container {
        text-align: center;
        padding: 1rem;
    }
    
    .gauge-value {
        font-size: 2.5rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .gauge-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-top: 0.25rem;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 3px;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .kpi-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .main-header h1 {
            font-size: 1.75rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_currency(value: float) -> str:
    """Format as Indian currency"""
    if value >= 10000000:
        return f"₹{value/10000000:.2f}Cr"
    elif value >= 100000:
        return f"₹{value/100000:.2f}L"
    elif value >= 1000:
        return f"₹{value/1000:.1f}K"
    return f"₹{value:,.0f}"


def format_number(value: float) -> str:
    """Format large numbers"""
    if value >= 1000000:
        return f"{value/1000000:.2f}M"
    elif value >= 1000:
        return f"{value/1000:.1f}K"
    return f"{value:,.0f}"


def get_change_html(change: float) -> str:
    """Get change indicator HTML"""
    if change > 0:
        return f'<span class="kpi-change up">↑ {change:.1f}%</span>'
    elif change < 0:
        return f'<span class="kpi-change down">↓ {abs(change):.1f}%</span>'
    return '<span class="kpi-change" style="background:rgba(255,255,255,0.1);color:var(--text-muted);">→ 0%</span>'


@st.cache_resource
def init_assistant(api_key: str, provider: str):
    try:
        return MultiAgentRetailAssistant(api_key=api_key, provider=provider)
    except Exception as e:
        st.error(f"Error: {e}")
        return None


@st.cache_resource
def init_processor():
    try:
        processor = RetailDataProcessor()
        try:
            processor.load_data()
        except:
            tables = processor.conn.execute("SHOW TABLES").fetchall()
            if tables:
                processor.tables_loaded = True
        return processor
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def get_stats(processor) -> Dict[str, Any]:
    """Get comprehensive statistics"""
    stats = processor.get_summary_statistics()
    amazon = stats.get('amazon_sales', {})
    
    # Calculate rates
    status_dist = stats.get('status_distribution', [])
    total = sum(s.get('count', 0) for s in status_dist)
    delivered = sum(s.get('count', 0) for s in status_dist 
                   if any(x in s.get('Status', '').lower() for x in ['delivered', 'shipped']))
    cancelled = sum(s.get('count', 0) for s in status_dist 
                   if 'cancel' in s.get('Status', '').lower())
    
    stats['fulfillment_rate'] = (delivered / total * 100) if total > 0 else 0
    stats['cancellation_rate'] = (cancelled / total * 100) if total > 0 else 0
    
    # Monthly trend
    try:
        trend_df = processor.execute_query("""
            SELECT strftime('%Y-%m', Date) as month,
                   COUNT(*) as orders,
                   SUM(Amount) as revenue
            FROM amazon_sales
            WHERE Date IS NOT NULL AND Amount IS NOT NULL
            GROUP BY strftime('%Y-%m', Date)
            ORDER BY month
            LIMIT 12
        """)
        stats['monthly_trend'] = trend_df.to_dict('records')
    except:
        stats['monthly_trend'] = []
    
    # Daily pattern
    try:
        daily_df = processor.execute_query("""
            SELECT strftime('%w', Date) as day_num,
                   COUNT(*) as orders,
                   SUM(Amount) as revenue
            FROM amazon_sales
            WHERE Date IS NOT NULL
            GROUP BY strftime('%w', Date)
            ORDER BY day_num
        """)
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        daily_df['day'] = daily_df['day_num'].astype(int).map(lambda x: days[x])
        stats['daily_pattern'] = daily_df.to_dict('records')
    except:
        stats['daily_pattern'] = []
    
    return stats


def create_trend_chart(data: List[Dict]) -> go.Figure:
    """Create revenue trend chart"""
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(data)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Bar(
        x=df['month'], y=df['revenue'], name='Revenue',
        marker=dict(color=df['revenue'], colorscale=[[0, '#667eea'], [1, '#764ba2']]),
        opacity=0.85
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['orders'], name='Orders',
        mode='lines+markers',
        line=dict(color='#10b981', width=3),
        marker=dict(size=8)
    ), secondary_y=True)
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        legend=dict(orientation='h', y=1.1, x=0.5, xanchor='center'),
        hovermode='x unified'
    )
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
    
    return fig


def create_category_chart(data: List[Dict]) -> go.Figure:
    """Create category performance chart"""
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(data)
    
    fig = go.Figure(go.Bar(
        y=df['Category'], x=df['revenue'],
        orientation='h',
        marker=dict(color=df['revenue'], colorscale='Viridis'),
        text=[format_currency(v) for v in df['revenue']],
        textposition='inside',
        textfont=dict(color='white', size=11)
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        yaxis=dict(autorange='reversed')
    )
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
    
    return fig


def create_state_map(data: List[Dict]) -> go.Figure:
    """Create state treemap"""
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(data[:10])
    
    fig = px.treemap(
        df, path=['state'], values='revenue',
        color='revenue', color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=300
    )
    fig.update_traces(
        textinfo='label+value',
        hovertemplate='<b>%{label}</b><br>Revenue: ₹%{value:,.0f}<extra></extra>'
    )
    
    return fig


def create_status_chart(data: List[Dict]) -> go.Figure:
    """Create order status donut chart"""
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(data[:6])
    
    colors = {'Shipped': '#10b981', 'Delivered': '#3b82f6', 'Cancelled': '#ef4444',
              'Pending': '#f59e0b', 'Returned': '#8b5cf6', 'Processing': '#06b6d4'}
    
    fig = go.Figure(go.Pie(
        labels=df['Status'], values=df['count'], hole=0.65,
        marker=dict(colors=[colors.get(s, '#667eea') for s in df['Status']]),
        textinfo='percent',
        textfont=dict(size=11, color='white')
    ))
    
    total = df['count'].sum()
    fig.add_annotation(
        text=f"<b>{format_number(total)}</b><br>Orders",
        x=0.5, y=0.5, font=dict(size=14, color='white'), showarrow=False
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        showlegend=True,
        legend=dict(orientation='h', y=-0.1, x=0.5, xanchor='center')
    )
    
    return fig


def create_daily_heatmap(data: List[Dict]) -> go.Figure:
    """Create daily pattern chart"""
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(data)
    
    fig = go.Figure(go.Bar(
        x=df['day'], y=df['orders'],
        marker=dict(color=df['orders'], colorscale=[[0, '#667eea'], [1, '#10b981']]),
        text=df['orders'].apply(lambda x: format_number(x)),
        textposition='outside'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=30, b=10),
        height=250
    )
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
    
    return fig


def create_gauge(value: float, title: str, max_val: float = 100, 
                 good_threshold: float = 75, color: str = '#667eea') -> go.Figure:
    """Create gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': '%', 'font': {'size': 36, 'color': 'white'}},
        gauge={
            'axis': {'range': [0, max_val], 'tickcolor': 'white'},
            'bar': {'color': color},
            'bgcolor': 'rgba(255,255,255,0.1)',
            'steps': [
                {'range': [0, max_val*0.5], 'color': 'rgba(239,68,68,0.2)'},
                {'range': [max_val*0.5, good_threshold], 'color': 'rgba(245,158,11,0.2)'},
                {'range': [good_threshold, max_val], 'color': 'rgba(16,185,129,0.2)'}
            ]
        }
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        height=200
    )
    
    return fig


def generate_excel_download(processor) -> bytes:
    """Generate Excel file for download"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        stats = processor.get_summary_statistics()
        amazon = stats.get('amazon_sales', {})
        summary_data = {
            'Metric': ['Total Orders', 'Total Revenue', 'Avg Order Value', 'Categories', 'States'],
            'Value': [amazon.get('total_orders', 0), amazon.get('total_revenue', 0),
                     amazon.get('avg_order_value', 0), amazon.get('unique_categories', 0),
                     amazon.get('unique_states', 0)]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        # Categories
        cats = stats.get('top_categories', [])
        if cats:
            pd.DataFrame(cats).to_excel(writer, sheet_name='Categories', index=False)
        
        # States
        states = stats.get('top_states', [])
        if states:
            pd.DataFrame(states).to_excel(writer, sheet_name='States', index=False)
        
        # Status
        status = stats.get('status_distribution', [])
        if status:
            pd.DataFrame(status).to_excel(writer, sheet_name='Status', index=False)
    
    return output.getvalue()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        # API Configuration
        openai_key = os.getenv("OPENAI_API_KEY", "")
        google_key = os.getenv("GOOGLE_API_KEY", "")
        
        provider = st.radio("AI Provider", ["OpenAI", "Google Gemini"],
                           index=1 if google_key and not openai_key else 0,
                           horizontal=True)
        
        api_key = st.text_input(
            "API Key", type="password",
            value=google_key if provider == "Google Gemini" else openai_key
        )
        
        if not api_key:
            st.warning("Enter API key to continue")
            st.stop()
        
        st.divider()
        
        # Navigation
        st.markdown("### 📍 Navigation")
        page = st.radio(
            "Select Page",
            ["📊 Dashboard", "📤 Upload Data", "💬 AI Assistant", 
             "🔍 Data Explorer", "📥 Export Reports"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Quick Stats
        st.markdown("### 📈 System Status")
        st.success("✓ System Online")
        st.info(f"📅 {datetime.now().strftime('%B %d, %Y')}")
        
        st.divider()
        
        with st.expander("ℹ️ About"):
            st.markdown("""
            **Retail Insights Pro**
            
            Enterprise analytics platform with:
            - 🤖 AI-Powered Analysis
            - 📊 Real-time Dashboards
            - 🔄 Universal Data Intake
            - 📥 Export & Reporting
            """)
    
    # Initialize
    assistant = init_assistant(api_key, provider)
    processor = init_processor()
    
    if not assistant or not processor:
        st.error("Initialization failed")
        st.stop()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Retail Insights Pro</h1>
        <p>Enterprise Analytics Platform • AI-Powered Business Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # PAGE: DASHBOARD
    # ========================================================================
    if page == "📊 Dashboard":
        stats = get_stats(processor)
        amazon = stats.get('amazon_sales', {})
        
        # KPI Cards
        st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">💰</div>
                <div class="kpi-value">{format_currency(amazon.get('total_revenue', 0))}</div>
                <div class="kpi-label">Total Revenue</div>
                {get_change_html(12.5)}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">📦</div>
                <div class="kpi-value">{format_number(amazon.get('total_orders', 0))}</div>
                <div class="kpi-label">Total Orders</div>
                {get_change_html(8.3)}
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">🎯</div>
                <div class="kpi-value">₹{amazon.get('avg_order_value', 0):,.0f}</div>
                <div class="kpi-label">Avg Order Value</div>
                {get_change_html(-2.1)}
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">✅</div>
                <div class="kpi-value">{stats.get('fulfillment_rate', 0):.1f}%</div>
                <div class="kpi-label">Fulfillment Rate</div>
                {get_change_html(3.2)}
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">🗺️</div>
                <div class="kpi-value">{amazon.get('unique_states', 0)}</div>
                <div class="kpi-label">States Covered</div>
                {get_change_html(0)}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Alerts
        alerts = []
        if stats.get('cancellation_rate', 0) > 20:
            alerts.append(('danger', '⚠️', f"High cancellation rate: {stats['cancellation_rate']:.1f}%"))
        elif stats.get('cancellation_rate', 0) > 10:
            alerts.append(('warning', '⚡', f"Cancellation rate: {stats['cancellation_rate']:.1f}%"))
        if stats.get('fulfillment_rate', 0) > 85:
            alerts.append(('success', '✨', f"Excellent fulfillment: {stats['fulfillment_rate']:.1f}%"))
        
        if alerts:
            for alert_type, icon, msg in alerts:
                st.markdown(f'<div class="alert {alert_type}">{icon} {msg}</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Charts Row 1
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-title">📈 Revenue & Orders Trend</div>', unsafe_allow_html=True)
            st.plotly_chart(create_trend_chart(stats.get('monthly_trend', [])), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-title">🏆 Top Categories</div>', unsafe_allow_html=True)
            st.plotly_chart(create_category_chart(stats.get('top_categories', [])), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Charts Row 2
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-title">🗺️ Revenue by State</div>', unsafe_allow_html=True)
            st.plotly_chart(create_state_map(stats.get('top_states', [])), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-title">📊 Order Status</div>', unsafe_allow_html=True)
            st.plotly_chart(create_status_chart(stats.get('status_distribution', [])), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Charts Row 3
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-title">✅ Fulfillment</div>', unsafe_allow_html=True)
            st.plotly_chart(create_gauge(stats.get('fulfillment_rate', 0), "Fulfillment", color='#10b981'), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-title">❌ Cancellation</div>', unsafe_allow_html=True)
            st.plotly_chart(create_gauge(stats.get('cancellation_rate', 0), "Cancellation", max_val=50, good_threshold=10, color='#ef4444'), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="chart-card"><div class="chart-title">📅 Daily Pattern</div>', unsafe_allow_html=True)
            st.plotly_chart(create_daily_heatmap(stats.get('daily_pattern', [])), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # AI Insights
        st.markdown('<div class="section-header"><h2>💡 AI Insights</h2></div>', unsafe_allow_html=True)
        
        top_cats = stats.get('top_categories', [])
        top_states = stats.get('top_states', [])
        
        insights = []
        if top_cats:
            insights.append(f"<strong>{top_cats[0]['Category']}</strong> is your top performer with {format_currency(top_cats[0]['revenue'])} revenue")
        if top_states:
            insights.append(f"<strong>{top_states[0]['state']}</strong> leads geographically with {top_states[0]['order_count']:,} orders")
        if stats.get('fulfillment_rate', 0) > 80:
            insights.append(f"Operations running strong with <strong>{stats['fulfillment_rate']:.1f}%</strong> fulfillment rate")
        
        for insight in insights[:3]:
            st.markdown(f'<div class="insight-card"><p>{insight}</p></div>', unsafe_allow_html=True)
        
        if st.button("🤖 Generate AI Summary", use_container_width=True):
            with st.spinner("AI analyzing..."):
                try:
                    summary = assistant.get_summary()
                    st.markdown(f'<div class="insight-card"><p>{summary}</p></div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # ========================================================================
    # PAGE: UPLOAD DATA
    # ========================================================================
    elif page == "📤 Upload Data":
        st.markdown('<div class="section-header"><h2>📤 Upload Your Data</h2></div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="insight-card">
            <p>Upload any data format - our AI will automatically detect and convert it for analysis.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Supported formats
        col1, col2, col3, col4 = st.columns(4)
        formats = [("📄", "CSV"), ("📊", "Excel"), ("📋", "JSON"), ("🔗", "API")]
        for col, (icon, fmt) in zip([col1, col2, col3, col4], formats):
            with col:
                st.markdown(f"""
                <div class="metric-mini">
                    <div class="value">{icon}</div>
                    <div class="label">{fmt}</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['csv', 'xlsx', 'xls', 'json'],
            help="Drag and drop or click to browse"
        )
        
        if uploaded_file:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # Preview
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith('.json'):
                    df = pd.read_json(uploaded_file)
                
                st.markdown("### 📋 Data Preview")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rows", format_number(len(df)))
                with col2:
                    st.metric("Columns", len(df.columns))
                with col3:
                    st.metric("Size", f"{uploaded_file.size/1024:.1f} KB")
                
                st.dataframe(df.head(10), use_container_width=True)
                
                # Schema
                with st.expander("📊 Column Details"):
                    schema_df = pd.DataFrame({
                        'Column': df.columns,
                        'Type': df.dtypes.astype(str),
                        'Non-Null': df.count().values,
                        'Sample': [str(df[col].iloc[0])[:50] if len(df) > 0 else '' for col in df.columns]
                    })
                    st.dataframe(schema_df, use_container_width=True)
                
                # Import options
                st.markdown("### ⚙️ Import Options")
                table_name = st.text_input("Table Name", value=uploaded_file.name.split('.')[0].replace(' ', '_').lower())
                
                if st.button("🚀 Import Data", use_container_width=True):
                    with st.spinner("Importing..."):
                        try:
                            # Save temp and load
                            temp_path = Path(f"temp_{uploaded_file.name}")
                            df.to_csv(temp_path, index=False)
                            
                            result = processor.load_csv_from_intake_agent(str(temp_path), table_name)
                            temp_path.unlink()  # Clean up
                            
                            st.success(f"✅ Imported {result['row_count']:,} rows to table '{result['table_name']}'")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            except Exception as e:
                st.error(f"Could not read file: {e}")
    
    # ========================================================================
    # PAGE: AI ASSISTANT
    # ========================================================================
    elif page == "💬 AI Assistant":
        st.markdown('<div class="section-header"><h2>💬 AI Assistant</h2></div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="insight-card">
            <p>Ask questions about your data in natural language. I'll analyze and provide insights.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick questions
        st.markdown("### 🚀 Quick Questions")
        
        questions = [
            "What are the top 5 selling categories?",
            "Which state has the highest revenue?",
            "How many orders were cancelled?",
            "What's the average order value?",
            "Show monthly sales trend",
            "Which products have low stock?"
        ]
        
        cols = st.columns(2)
        for i, q in enumerate(questions):
            with cols[i % 2]:
                if st.button(q, key=f"q_{i}", use_container_width=True):
                    st.session_state.current_query = q
        
        st.markdown("---")
        
        # Chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        for msg in st.session_state.chat_history:
            role = msg["role"]
            st.markdown(f"""
            <div class="chat-msg {role}">
                <div class="role">{'👤 You' if role == 'user' else '🤖 AI'}</div>
                <div class="content">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Input
        query = st.text_input(
            "Your question:",
            value=st.session_state.get("current_query", ""),
            placeholder="Ask anything about your retail data..."
        )
        
        if "current_query" in st.session_state:
            del st.session_state.current_query
        
        col1, col2 = st.columns([5, 1])
        with col1:
            ask = st.button("🚀 Ask", use_container_width=True)
        with col2:
            if st.button("🗑️", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        if ask and query:
            st.session_state.chat_history.append({"role": "user", "content": query})
            
            with st.spinner("Thinking..."):
                try:
                    response = assistant.process_query(query, query_type="qa")
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # ========================================================================
    # PAGE: DATA EXPLORER
    # ========================================================================
    elif page == "🔍 Data Explorer":
        st.markdown('<div class="section-header"><h2>🔍 Data Explorer</h2></div>', unsafe_allow_html=True)
        
        # Tables
        tables = processor.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        selected = st.selectbox("Select Table", table_names)
        
        if selected:
            # Stats
            count = processor.conn.execute(f"SELECT COUNT(*) FROM {selected}").fetchone()[0]
            schema = processor.conn.execute(f"DESCRIBE {selected}").fetchdf()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", format_number(count))
            with col2:
                st.metric("Columns", len(schema))
            with col3:
                st.metric("Table", selected)
            
            # Schema
            with st.expander("📋 Schema", expanded=True):
                st.dataframe(schema, use_container_width=True)
            
            # Sample
            st.markdown("### 📊 Sample Data")
            sample = processor.execute_query(f"SELECT * FROM {selected} LIMIT 100")
            st.dataframe(sample, use_container_width=True, height=300)
            
            # Custom Query
            st.markdown("### 💻 Custom SQL")
            sql = st.text_area("Query", value=f"SELECT * FROM {selected} LIMIT 10", height=100)
            
            if st.button("▶️ Run Query", use_container_width=True):
                try:
                    result = processor.execute_query(sql)
                    st.success(f"✅ {len(result)} rows returned")
                    st.dataframe(result, use_container_width=True)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # ========================================================================
    # PAGE: EXPORT REPORTS
    # ========================================================================
    elif page == "📥 Export Reports":
        st.markdown('<div class="section-header"><h2>📥 Export Reports</h2></div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="insight-card">
            <p>Download your analytics data in various formats for reporting and further analysis.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Excel Report")
            st.markdown("Complete analytics report with multiple sheets")
            
            excel_data = generate_excel_download(processor)
            st.download_button(
                "📥 Download Excel",
                data=excel_data,
                file_name=f"retail_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            st.markdown("### 📄 CSV Export")
            st.markdown("Export individual tables as CSV")
            
            tables = processor.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            table_to_export = st.selectbox("Select Table", table_names, key="export_table")
            
            if table_to_export:
                df = processor.execute_query(f"SELECT * FROM {table_to_export}")
                csv = df.to_csv(index=False)
                
                st.download_button(
                    "📥 Download CSV",
                    data=csv,
                    file_name=f"{table_to_export}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        st.markdown("---")
        
        # Summary Stats Download
        st.markdown("### 📈 Summary Statistics")
        
        stats = processor.get_summary_statistics()
        stats_json = json.dumps(stats, indent=2, default=str)
        
        st.download_button(
            "📥 Download JSON Summary",
            data=stats_json,
            file_name=f"summary_stats_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
