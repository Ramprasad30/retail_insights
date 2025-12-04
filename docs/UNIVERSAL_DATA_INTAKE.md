# Universal Data Intake Agent

## Overview

The Universal Data Intake Agent is a powerful pre-processing system that accepts **any data source format** and converts it to CSV, enabling seamless integration with the existing retail analytics pipeline without modifying any existing logic.

## Architecture

The agent follows a multi-agent architecture with 5 specialized sub-agents:

### Agent 1: Data Format Detector
- **Purpose**: Auto-detects the format of incoming data
- **Supported Detection**:
  - File extensions (.csv, .xlsx, .json, .apf, .txt)
  - Content analysis (magic bytes, structure)
  - URL/API endpoint detection
  - Database connection string detection

### Agent 2: Data Fetcher
- **Purpose**: Retrieves data from various sources
- **Capabilities**:
  - Local file reading
  - HTTP/HTTPS API calls
  - SQL database queries
  - MongoDB/NoSQL queries

### Agent 3: Data Converter
- **Purpose**: Converts raw data to pandas DataFrame
- **Supported Formats**:
  - CSV (passthrough)
  - Excel (XLS/XLSX)
  - JSON (arrays, objects, nested structures)
  - APF (mainframe fixed-width files)
  - Semi-structured text files
  - SQL query results
  - MongoDB collections
  - API responses

### Agent 4: CSV Normalizer
- **Purpose**: Standardizes DataFrame structure
- **Operations**:
  - Column name cleaning
  - Missing value handling
  - Data type consistency
  - Duplicate removal (optional)

### Agent 5: Data Validator
- **Purpose**: Ensures data quality before export
- **Checks**:
  - Empty data detection
  - Required columns validation
  - Null percentage warnings
  - Duplicate row detection

## Supported Input Formats

### ✅ CSV Files
- **Detection**: File extension `.csv` or content analysis
- **Processing**: Direct passthrough (no conversion needed)
- **Example**:
  ```python
  agent.process("data/sales.csv")
  ```

### ✅ Excel Files
- **Detection**: File extensions `.xls`, `.xlsx`, `.xlsm`
- **Processing**: Reads specified sheet (default: first sheet)
- **Example**:
  ```python
  agent.process("data/sales.xlsx", sheet_name=0)
  ```

### ✅ JSON Files
- **Detection**: File extension `.json` or JSON content
- **Processing**: Handles arrays, objects, nested structures
- **Example**:
  ```python
  agent.process("data/sales.json")
  ```

### ✅ APF (Mainframe) Files
- **Detection**: File extension `.apf`, `.ebcdic`, or fixed-width content
- **Processing**: Fixed-width parsing with auto-detection
- **Example**:
  ```python
  agent.process("data/mainframe.apf", widths=[10, 20, 15], column_names=["col1", "col2", "col3"])
  ```

### ✅ Semi-Structured Text Files
- **Detection**: File extensions `.txt`, `.log`, `.dat`
- **Processing**: Auto-detects delimiters (comma, tab, pipe, etc.)
- **Example**:
  ```python
  agent.process("data/logs.txt")
  ```

### ✅ SQL Databases
- **Detection**: Connection strings (`postgresql://`, `mysql://`, `sqlite://`, etc.)
- **Processing**: Executes SQL query and converts results
- **Example**:
  ```python
  agent.process(
      "postgresql://user:pass@localhost/dbname",
      query="SELECT * FROM sales LIMIT 1000"
  )
  ```

### ✅ NoSQL Databases (MongoDB)
- **Detection**: MongoDB connection strings (`mongodb://`, `mongodb+srv://`)
- **Processing**: Queries collection and converts to DataFrame
- **Example**:
  ```python
  agent.process(
      "mongodb://localhost:27017/",
      database="sales_db",
      collection="orders",
      query={"status": "completed"},
      limit=1000
  )
  ```

### ✅ API Endpoints
- **Detection**: URLs starting with `http://` or `https://`
- **Processing**: Fetches JSON/CSV/text and converts
- **Example**:
  ```python
  agent.process(
      "https://api.example.com/sales",
      timeout=30,
      headers={"Authorization": "Bearer token"}
  )
  ```

## Usage

### Basic Usage

```python
from backend.data_intake_agent import UniversalDataIntakeAgent

# Initialize the agent
agent = UniversalDataIntakeAgent()

# Process any data source
result = agent.process("data/sales.xlsx", output_filename="sales_converted.csv")

if result['status'] == 'success':
    print(f"CSV saved to: {result['csv_path']}")
    print(f"Rows: {result['stats']['rows']}")
    print(f"Columns: {result['stats']['columns']}")
else:
    print(f"Error: {result['error']}")
```

### Integration with Existing System

```python
from backend.data_intake_agent import UniversalDataIntakeAgent
from backend.data_processor import RetailDataProcessor

# Step 1: Convert any format to CSV
agent = UniversalDataIntakeAgent()
result = agent.process("data/sales.json", output_filename="sales.csv")

if result['status'] == 'success':
    # Step 2: Load into existing RetailDataProcessor
    processor = RetailDataProcessor()
    load_result = processor.load_csv_from_intake_agent(
        csv_path=result['csv_path'],
        table_name="sales_data",
        replace_existing=True
    )
    
    # Step 3: Use existing query system
    df = processor.execute_query("SELECT * FROM sales_data LIMIT 10")
    print(df)
```

### Advanced Usage

```python
# Process multiple files
sources = ["file1.xlsx", "file2.json", "file3.csv"]
results = agent.process_multiple(sources)

# Custom normalization options
result = agent.process(
    "data/sales.xlsx",
    output_filename="sales.csv",
    fillna=True,              # Fill missing values
    fillna_value="",          # Fill with empty string
    remove_duplicates=True    # Remove duplicate rows
)

# SQL database with custom query
result = agent.process(
    "postgresql://user:pass@localhost/db",
    query="SELECT * FROM sales WHERE date > '2024-01-01'",
    output_filename="recent_sales.csv"
)

# MongoDB with filter
result = agent.process(
    "mongodb://localhost:27017/",
    database="retail",
    collection="orders",
    query={"status": "completed", "amount": {"$gt": 1000}},
    limit=5000,
    output_filename="large_orders.csv"
)
```

## Output Format

The agent returns a dictionary with the following structure:

```python
{
    'status': 'success' | 'error',
    'csv_path': '/path/to/converted.csv',  # Only if success
    'format_detected': 'excel' | 'json' | 'csv' | etc.,
    'validation': {
        'status': 'PASSED' | 'FAILED' | 'WARNING',
        'warnings': ['warning1', 'warning2'],
        'errors': ['error1'],
        'stats': {
            'row_count': 1000,
            'column_count': 10,
            'null_percentage': 5.2,
            'duplicate_rows': 0
        }
    },
    'stats': {
        'rows': 1000,
        'columns': 10,
        'file_size_mb': 0.5
    },
    'error': 'error message'  # Only if status is 'error'
}
```

## Configuration

### Output Directory

By default, converted CSV files are saved to a temporary directory. You can specify a custom output directory:

```python
from pathlib import Path

agent = UniversalDataIntakeAgent(
    output_dir=Path("converted_data")
)
```

### Format-Specific Options

#### Excel
```python
agent.process(
    "data.xlsx",
    sheet_name=0,           # Sheet index or name
    header=0,               # Row to use as header
    skiprows=0              # Rows to skip
)
```

#### JSON
```python
agent.process(
    "data.json",
    # JSON is auto-detected and parsed
    # Handles arrays, objects, nested structures
)
```

#### APF (Fixed-Width)
```python
agent.process(
    "data.apf",
    widths=[10, 20, 15, 30],           # Column widths
    column_names=["col1", "col2", "col3", "col4"]
)
```

#### SQL
```python
agent.process(
    "postgresql://user:pass@localhost/db",
    query="SELECT * FROM table WHERE condition"
)
```

#### MongoDB
```python
agent.process(
    "mongodb://localhost:27017/",
    database="dbname",
    collection="collection_name",
    query={"field": "value"},  # MongoDB query filter
    limit=1000                  # Max documents
)
```

#### API
```python
agent.process(
    "https://api.example.com/data",
    timeout=30,                    # Request timeout
    headers={"Authorization": "Bearer token"}
)
```

## Error Handling

The agent handles errors gracefully:

```python
result = agent.process("invalid_source.xlsx")

if result['status'] == 'error':
    print(f"Error: {result['error']}")
    print(f"Format detected: {result.get('format_detected', 'unknown')}")
```

Common errors:
- **FileNotFoundError**: File doesn't exist
- **ImportError**: Required library not installed (requests, sqlalchemy, pymongo)
- **ValueError**: Unsupported format or invalid data structure
- **ConnectionError**: Database/API connection failed

## Dependencies

### Required
- `pandas` - Data manipulation
- `openpyxl` - Excel file support

### Optional (for specific formats)
- `requests` - API endpoints
- `sqlalchemy` - SQL databases
- `pymongo` - MongoDB/NoSQL

Install all dependencies:
```bash
pip install -r requirements.txt
```

## Best Practices

1. **Always check validation results**:
   ```python
   if result['validation']['status'] == 'FAILED':
       print("Data validation failed!")
   ```

2. **Handle warnings**:
   ```python
   if result['validation']['warnings']:
       for warning in result['validation']['warnings']:
           print(f"Warning: {warning}")
   ```

3. **Use descriptive table names** when loading into DuckDB:
   ```python
   processor.load_csv_from_intake_agent(
       csv_path=result['csv_path'],
       table_name="sales_2024_q1"  # Descriptive name
   )
   ```

4. **Process large files in chunks** (for very large datasets):
   ```python
   # For files > 1GB, consider chunking
   # The agent handles this automatically for most formats
   ```

5. **Validate data sources** before processing:
   ```python
   format_type = DataFormatDetector.detect_format("data.xlsx")
   if format_type == 'unknown':
       print("Format not recognized!")
   ```

## Examples

See `scripts/example_data_intake.py` for comprehensive examples including:
- CSV passthrough
- Excel conversion
- JSON conversion
- API endpoint processing
- Full integration with existing system

## Architecture Benefits

✅ **Backward Compatible**: Existing CSV pipeline unchanged
✅ **Future-Proof**: Easy to add new formats
✅ **Modular**: Each agent is independent
✅ **Error-Resilient**: Graceful error handling
✅ **Validated**: Data quality checks before export
✅ **Extensible**: Simple to add new format handlers

## Troubleshooting

### Issue: "requests library required"
**Solution**: `pip install requests`

### Issue: "sqlalchemy required"
**Solution**: `pip install sqlalchemy`

### Issue: "pymongo required"
**Solution**: `pip install pymongo`

### Issue: Format not detected correctly
**Solution**: Specify format explicitly or check file extension

### Issue: Large files cause memory issues
**Solution**: Process in chunks or use distributed processing (see scalability.py)

## Future Enhancements

Potential additions:
- Parquet format support
- XML format support
- Cloud storage (S3, GCS, Azure) support
- Streaming data processing
- Parallel processing for multiple files
- Data transformation rules engine

