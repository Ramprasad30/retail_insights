"""
Example Usage: Universal Data Intake Agent

This script demonstrates how to use the Universal Data Intake Agent
to convert various data formats to CSV and integrate with the existing system.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data_intake_agent import UniversalDataIntakeAgent
from backend.data_processor import RetailDataProcessor


def example_csv_passthrough():
    """Example 1: CSV passthrough (no conversion needed)"""
    print("\n=== Example 1: CSV Passthrough ===")
    
    agent = UniversalDataIntakeAgent()
    
    # Use existing CSV file
    csv_file = Path("data/Sales Dataset/Sales Dataset/Amazon Sale Report.csv")
    
    if csv_file.exists():
        result = agent.process(csv_file, output_filename="amazon_sales_converted.csv")
        print(f"Status: {result['status']}")
        print(f"CSV Path: {result.get('csv_path', 'N/A')}")
        print(f"Format Detected: {result.get('format_detected', 'N/A')}")
        print(f"Stats: {result.get('stats', {})}")
    else:
        print(f"File not found: {csv_file}")


def example_excel_conversion():
    """Example 2: Convert Excel file to CSV"""
    print("\n=== Example 2: Excel Conversion ===")
    
    agent = UniversalDataIntakeAgent()
    
    # Example: Convert Excel file (if you have one)
    excel_file = Path("example_data.xlsx")
    
    if excel_file.exists():
        result = agent.process(
            excel_file,
            output_filename="excel_converted.csv",
            sheet_name=0  # First sheet
        )
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"CSV Path: {result['csv_path']}")
            print(f"Rows: {result['stats']['rows']}")
            print(f"Columns: {result['stats']['columns']}")
    else:
        print(f"Excel file not found: {excel_file}")
        print("Note: Create an Excel file to test this example")


def example_json_conversion():
    """Example 3: Convert JSON file to CSV"""
    print("\n=== Example 3: JSON Conversion ===")
    
    agent = UniversalDataIntakeAgent()
    
    # Create a sample JSON file for demonstration
    import json
    import tempfile
    
    sample_data = [
        {"name": "Product A", "price": 100, "category": "Electronics"},
        {"name": "Product B", "price": 200, "category": "Clothing"},
        {"name": "Product C", "price": 150, "category": "Electronics"}
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_data, f)
        json_file = Path(f.name)
    
    try:
        result = agent.process(json_file, output_filename="json_converted.csv")
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"CSV Path: {result['csv_path']}")
            print(f"Rows: {result['stats']['rows']}")
            print(f"Validation: {result['validation']['status']}")
    finally:
        # Clean up
        json_file.unlink()


def example_api_endpoint():
    """Example 4: Convert API endpoint data to CSV"""
    print("\n=== Example 4: API Endpoint Conversion ===")
    
    agent = UniversalDataIntakeAgent()
    
    # Example: Public API endpoint
    api_url = "https://jsonplaceholder.typicode.com/users"
    
    try:
        result = agent.process(
            api_url,
            output_filename="api_users_converted.csv",
            timeout=30
        )
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"CSV Path: {result['csv_path']}")
            print(f"Rows: {result['stats']['rows']}")
            print(f"Format Detected: {result['format_detected']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error processing API: {e}")
        print("Note: Requires 'requests' library: pip install requests")


def example_integration_with_existing_system():
    """Example 5: Full integration with existing RetailDataProcessor"""
    print("\n=== Example 5: Integration with Existing System ===")
    
    # Step 1: Convert any data source to CSV
    agent = UniversalDataIntakeAgent()
    
    # Example: Convert a JSON file
    import json
    import tempfile
    
    sample_sales_data = [
        {"order_id": "ORD001", "amount": 1000, "category": "Electronics", "status": "Delivered"},
        {"order_id": "ORD002", "amount": 2000, "category": "Clothing", "status": "Pending"},
        {"order_id": "ORD003", "amount": 1500, "category": "Electronics", "status": "Delivered"}
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_sales_data, f)
        json_file = Path(f.name)
    
    try:
        # Convert to CSV
        result = agent.process(json_file, output_filename="sales_data_converted.csv")
        
        if result['status'] == 'success':
            csv_path = result['csv_path']
            print(f"✓ Converted to CSV: {csv_path}")
            
            # Step 2: Load into existing RetailDataProcessor
            processor = RetailDataProcessor()
            
            load_result = processor.load_csv_from_intake_agent(
                csv_path=csv_path,
                table_name="custom_sales_data",
                replace_existing=True
            )
            
            print(f"✓ Loaded into DuckDB table: {load_result['table_name']}")
            print(f"✓ Rows loaded: {load_result['row_count']}")
            
            # Step 3: Query the data using existing system
            query_result = processor.execute_query(
                "SELECT category, SUM(amount) as total FROM custom_sales_data GROUP BY category"
            )
            print(f"\n✓ Query Results:")
            print(query_result)
            
            processor.close()
        else:
            print(f"✗ Conversion failed: {result.get('error', 'Unknown error')}")
    finally:
        # Clean up
        json_file.unlink()


def main():
    """Run all examples"""
    print("=" * 60)
    print("Universal Data Intake Agent - Example Usage")
    print("=" * 60)
    
    # Run examples
    example_csv_passthrough()
    example_excel_conversion()
    example_json_conversion()
    example_api_endpoint()
    example_integration_with_existing_system()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

