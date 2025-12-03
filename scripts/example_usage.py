import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def example_1_simple_query():
    print("\n" + "="*60)
    print("Example 1: Simple Q&A Query")
    print("="*60)
    
    from backend.agents import MultiAgentRetailAssistant
    
    # Set your API key
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    
    if api_key == "your-api-key-here":
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        return
    
    # Initialize assistant
    print("🔄 Initializing Multi-Agent Assistant...")
    assistant = MultiAgentRetailAssistant(api_key=api_key)
    
    # Ask a question
    question = "What are the top 5 selling categories?"
    print(f"\n📝 Question: {question}")
    
    print("🤖 Processing with multi-agent system...")
    response = assistant.process_query(question, query_type="qa")
    
    print(f"\n💡 Answer:\n{response}")
    
    # Clean up
    assistant.close()


def example_2_generate_summary():
    print("\n" + "="*60)
    print("Example 2: Generate Summary")
    print("="*60)
    
    from backend.agents import MultiAgentRetailAssistant
    
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    
    if api_key == "your-api-key-here":
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        return
    
    # Initialize assistant
    print("🔄 Initializing Multi-Agent Assistant...")
    assistant = MultiAgentRetailAssistant(api_key=api_key)
    
    # Generate summary
    print("📊 Generating comprehensive summary...")
    summary = assistant.get_summary()
    
    print(f"\n📈 Summary:\n{summary}")
    
    # Clean up
    assistant.close()


def example_3_data_processor():
    print("\n" + "="*60)
    print("Example 3: Direct Data Processor Usage")
    print("="*60)
    
    from backend.data_processor import RetailDataProcessor
    
    # Initialize processor
    print("🔄 Initializing Data Processor...")
    processor = RetailDataProcessor()
    
    # Load data
    print("📁 Loading data...")
    stats = processor.load_data()
    print(f"✅ Data loaded: {stats}")
    
    # Execute custom SQL query
    print("\n🔍 Executing custom query...")
    query = """
        SELECT 
            Category,
            COUNT(*) as order_count,
            SUM(CAST(Amount AS DOUBLE)) as total_revenue,
            AVG(CAST(Amount AS DOUBLE)) as avg_order_value
        FROM amazon_sales
        WHERE Amount IS NOT NULL AND Amount != '' AND Category IS NOT NULL
        GROUP BY Category
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    
    result = processor.execute_query(query)
    print("\n📊 Top 5 Categories:")
    print(result.to_string(index=False))
    
    # Get summary statistics
    print("\n📈 Summary Statistics:")
    summary = processor.get_summary_statistics()
    
    amazon_stats = summary.get('amazon_sales', {})
    print(f"  Total Orders: {amazon_stats.get('total_orders', 0):,}")
    print(f"  Total Revenue: ₹{amazon_stats.get('total_revenue', 0):,.2f}")
    print(f"  Avg Order Value: ₹{amazon_stats.get('avg_order_value', 0):,.2f}")
    
    # Clean up
    processor.close()


def example_4_multiple_queries():
    print("\n" + "="*60)
    print("Example 4: Multiple Queries")
    print("="*60)
    
    from backend.agents import MultiAgentRetailAssistant
    
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    
    if api_key == "your-api-key-here":
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        return
    
    # Initialize assistant once
    print("🔄 Initializing Multi-Agent Assistant...")
    assistant = MultiAgentRetailAssistant(api_key=api_key)
    
    # Multiple questions
    questions = [
        "What are the top 3 states by revenue?",
        "How many orders were cancelled?",
        "What is the average order value?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"Question {i}: {question}")
        print('='*60)
        
        response = assistant.process_query(question, query_type="qa")
        print(f"\nAnswer:\n{response}")
    
    # Clean up
    assistant.close()


def example_5_export_data():
    print("\n" + "="*60)
    print("Example 5: Export Query Results")
    print("="*60)
    
    from backend.data_processor import RetailDataProcessor
    import pandas as pd
    
    # Initialize processor
    print("🔄 Initializing Data Processor...")
    processor = RetailDataProcessor()
    processor.load_data()
    
    # Execute query
    print("\n🔍 Executing query...")
    query = """
        SELECT 
            "ship-state" as state,
            COUNT(*) as order_count,
            SUM(CAST(Amount AS DOUBLE)) as revenue
        FROM amazon_sales
        WHERE Amount IS NOT NULL AND Amount != '' AND "ship-state" IS NOT NULL
        GROUP BY "ship-state"
        ORDER BY revenue DESC
    """
    
    result = processor.execute_query(query)
    
    # Export to CSV
    output_file = "state_revenue_report.csv"
    result.to_csv(output_file, index=False)
    print(f"✅ Exported to {output_file}")
    
    # Export to Excel (optional)
    try:
        excel_file = "state_revenue_report.xlsx"
        result.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"✅ Exported to {excel_file}")
    except ImportError:
        print("⚠️  openpyxl not installed, skipping Excel export")
    
    # Show preview
    print("\n📊 Preview (first 10 rows):")
    print(result.head(10).to_string(index=False))
    
    # Clean up
    processor.close()


def main():
    print("="*60)
    print("🛍️  Retail Insights Assistant - Usage Examples")
    print("="*60)
    
    print("\nAvailable Examples:")
    print("1. Simple Q&A query")
    print("2. Generate comprehensive summary")
    print("3. Direct data processor usage")
    print("4. Multiple queries in sequence")
    print("5. Export query results")
    
    choice = input("\nSelect example (1-5) or 'all': ").strip()
    
    if choice == '1':
        example_1_simple_query()
    elif choice == '2':
        example_2_generate_summary()
    elif choice == '3':
        example_3_data_processor()
    elif choice == '4':
        example_4_multiple_queries()
    elif choice == '5':
        example_5_export_data()
    elif choice.lower() == 'all':
        # Run data processor example (no API key needed)
        example_3_data_processor()
        example_5_export_data()
        
        # Ask before running API examples
        response = input("\n\nRun API-based examples? (requires OpenAI API key) (y/n): ")
        if response.lower() == 'y':
            example_1_simple_query()
            example_2_generate_summary()
            example_4_multiple_queries()
    else:
        print("Invalid choice")
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    main()

