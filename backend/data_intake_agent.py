"""
Universal Data Intake Agent

This agent accepts any data source format and converts it to CSV
for seamless integration with the existing RetailDataProcessor pipeline.

Supported formats:
- CSV (passthrough)
- Excel (XLS/XLSX)
- JSON
- APF (mainframe files)
- Semi-structured text files
- SQL/NoSQL database connections
- API endpoints
"""

import pandas as pd
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
import tempfile
import os

# Optional imports for various formats
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from sqlalchemy import create_engine, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

try:
    import pymongo
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFormatDetector:
    """Agent 1: Data Source Classifier - Auto-detects data format"""
    
    @staticmethod
    def detect_format(data_source: Union[str, Path]) -> str:
        """
        Detect the format of the data source.
        
        Returns:
            Format type: 'csv', 'excel', 'json', 'apf', 'text', 'api', 'sql', 'nosql', 'unknown'
        """
        source_str = str(data_source).lower()
        
        # Check if it's a URL/API endpoint
        if source_str.startswith(('http://', 'https://')):
            return 'api'
        
        # Check if it's a database connection string
        if any(db in source_str for db in ['postgresql://', 'mysql://', 'sqlite://', 'oracle://', 'mssql://']):
            return 'sql'
        
        if source_str.startswith('mongodb://') or source_str.startswith('mongodb+srv://'):
            return 'nosql'
        
        # Check file extension
        path = Path(data_source)
        if not path.exists():
            # If file doesn't exist, try to infer from extension
            ext = path.suffix.lower()
        else:
            ext = path.suffix.lower()
        
        # Extension-based detection
        if ext == '.csv':
            return 'csv'
        elif ext in ['.xls', '.xlsx', '.xlsm']:
            return 'excel'
        elif ext == '.json':
            return 'json'
        elif ext == '.apf' or ext == '.ebcdic':
            return 'apf'
        elif ext in ['.txt', '.log', '.dat']:
            return 'text'
        
        # Content-based detection (if file exists)
        if path.exists():
            try:
                # Try to read first few bytes
                with open(path, 'rb') as f:
                    header = f.read(1024)
                
                # Check for Excel magic bytes
                if header.startswith(b'\xd0\xcf\x11\xe0') or header.startswith(b'PK\x03\x04'):
                    return 'excel'
                
                # Check for JSON
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    return 'json'
                except:
                    pass
                
                # Check for CSV (has commas or semicolons)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if ',' in first_line or ';' in first_line:
                            return 'csv'
                except:
                    pass
                
                # Check for APF (EBCDIC or fixed-width)
                if len(header) > 80 and all(32 <= b <= 126 or b in [9, 10, 13] for b in header[:80]):
                    # Might be fixed-width text
                    return 'apf'
                
            except Exception as e:
                logger.warning(f"Error detecting format: {e}")
        
        return 'unknown'


class DataFetcher:
    """Agent 2: Data Fetching Agent - Fetches data from various sources"""
    
    @staticmethod
    def fetch(data_source: Union[str, Path], **kwargs) -> Any:
        """
        Fetch data from the source.
        
        Returns:
            Raw data (file path, DataFrame, or raw content)
        """
        format_type = DataFormatDetector.detect_format(data_source)
        logger.info(f"Detected format: {format_type} for source: {data_source}")
        
        if format_type == 'csv':
            return str(data_source)  # Return path as-is
        
        elif format_type == 'excel':
            return str(data_source)  # Return path for converter
        
        elif format_type == 'json':
            if isinstance(data_source, Path) or os.path.exists(str(data_source)):
                return str(data_source)  # File path
            else:
                # Assume it's JSON string
                return json.loads(str(data_source))
        
        elif format_type == 'api':
            if not REQUESTS_AVAILABLE:
                raise ImportError("requests library required for API endpoints. Install with: pip install requests")
            
            timeout = kwargs.get('timeout', 30)
            headers = kwargs.get('headers', {})
            
            response = requests.get(str(data_source), timeout=timeout, headers=headers)
            response.raise_for_status()
            
            # Try to parse as JSON first
            try:
                return response.json()
            except:
                # Return raw text
                return response.text
        
        elif format_type == 'sql':
            if not SQLALCHEMY_AVAILABLE:
                raise ImportError("sqlalchemy required for SQL databases. Install with: pip install sqlalchemy")
            
            query = kwargs.get('query', 'SELECT * FROM table_name LIMIT 1000')
            engine = create_engine(str(data_source))
            
            with engine.connect() as conn:
                result = conn.execute(text(query))
                columns = result.keys()
                rows = result.fetchall()
                return pd.DataFrame(rows, columns=columns)
        
        elif format_type == 'nosql':
            if not PYMONGO_AVAILABLE:
                raise ImportError("pymongo required for MongoDB. Install with: pip install pymongo")
            
            # Parse MongoDB connection string
            client = pymongo.MongoClient(str(data_source))
            db_name = kwargs.get('database', 'test')
            collection_name = kwargs.get('collection', 'data')
            query = kwargs.get('query', {})
            limit = kwargs.get('limit', 1000)
            
            db = client[db_name]
            collection = db[collection_name]
            
            cursor = collection.find(query).limit(limit)
            data = list(cursor)
            
            # Convert to DataFrame
            if data:
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
        
        elif format_type in ['apf', 'text']:
            return str(data_source)  # Return path for converter
        
        else:
            raise ValueError(f"Unsupported data source format: {format_type}")


class DataConverter:
    """Agent 3: Conversion Agent - Converts raw data to Pandas DataFrame"""
    
    @staticmethod
    def convert_to_dataframe(data: Any, format_type: str, **kwargs) -> pd.DataFrame:
        """
        Convert raw data to pandas DataFrame.
        
        Args:
            data: Raw data (path, dict, list, etc.)
            format_type: Detected format type
            **kwargs: Additional parameters for conversion
        
        Returns:
            pandas DataFrame
        """
        logger.info(f"Converting {format_type} to DataFrame...")
        
        if format_type == 'csv':
            # CSV passthrough
            return pd.read_csv(data, **kwargs)
        
        elif format_type == 'excel':
            # Excel files
            sheet_name = kwargs.get('sheet_name', 0)
            return pd.read_excel(data, sheet_name=sheet_name, **kwargs)
        
        elif format_type == 'json':
            if isinstance(data, str):
                # File path
                with open(data, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            else:
                # Already parsed JSON
                json_data = data
            
            # Handle different JSON structures
            if isinstance(json_data, list):
                return pd.DataFrame(json_data)
            elif isinstance(json_data, dict):
                # Try to find the data array
                if 'data' in json_data:
                    return pd.DataFrame(json_data['data'])
                elif 'results' in json_data:
                    return pd.DataFrame(json_data['results'])
                elif 'items' in json_data:
                    return pd.DataFrame(json_data['items'])
                else:
                    # Flatten dict
                    return pd.DataFrame([json_data])
            else:
                raise ValueError(f"Unsupported JSON structure: {type(json_data)}")
        
        elif format_type == 'api':
            # API response (already parsed JSON or text)
            if isinstance(data, dict) or isinstance(data, list):
                return DataConverter.convert_to_dataframe(data, 'json')
            else:
                # Try to parse as CSV
                from io import StringIO
                return pd.read_csv(StringIO(data))
        
        elif format_type == 'sql':
            # Already a DataFrame from SQL query
            return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
        
        elif format_type == 'nosql':
            # Already a DataFrame from MongoDB
            return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
        
        elif format_type == 'apf':
            return DataConverter._parse_apf_file(data, **kwargs)
        
        elif format_type == 'text':
            return DataConverter._parse_text_file(data, **kwargs)
        
        else:
            raise ValueError(f"Cannot convert format: {format_type}")
    
    @staticmethod
    def _parse_apf_file(file_path: str, **kwargs) -> pd.DataFrame:
        """
        Parse APF (mainframe) files.
        APF files are typically fixed-width or EBCDIC encoded.
        """
        # Try fixed-width first
        widths = kwargs.get('widths', None)
        col_names = kwargs.get('column_names', None)
        
        if widths and col_names:
            return pd.read_fwf(file_path, widths=widths, names=col_names, **kwargs)
        
        # Try to auto-detect fixed-width
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                # Assume 80-character fixed width (common in mainframes)
                if len(first_line) >= 80:
                    # Try to split into columns
                    chunks = [first_line[i:i+10] for i in range(0, len(first_line), 10)]
                    return pd.read_fwf(file_path, widths=[10]*len(chunks), **kwargs)
        except:
            pass
        
        # Fallback: treat as CSV
        return pd.read_csv(file_path, **kwargs)
    
    @staticmethod
    def _parse_text_file(file_path: str, **kwargs) -> pd.DataFrame:
        """
        Parse semi-structured text files.
        Attempts to detect delimiters and structure.
        """
        # Try common delimiters
        delimiters = [',', '\t', '|', ';', ' ']
        
        for delimiter in delimiters:
            try:
                df = pd.read_csv(file_path, delimiter=delimiter, **kwargs)
                if len(df.columns) > 1:
                    return df
            except:
                continue
        
        # Try fixed-width
        try:
            return pd.read_fwf(file_path, **kwargs)
        except:
            pass
        
        # Last resort: single column
        return pd.read_csv(file_path, delimiter='\n', names=['content'], **kwargs)


class CSVNormalizer:
    """Agent 4: CSV Normalizer Agent - Standardizes DataFrame to clean CSV"""
    
    @staticmethod
    def normalize(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Normalize DataFrame to ensure CSV compatibility.
        
        Operations:
        - Clean column names
        - Handle missing values
        - Ensure consistent data types
        - Remove duplicates if requested
        """
        logger.info(f"Normalizing DataFrame with {len(df)} rows and {len(df.columns)} columns...")
        
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # Clean column names
        df.columns = [CSVNormalizer._clean_column_name(col) for col in df.columns]
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Handle missing values based on kwargs
        if kwargs.get('fillna', False):
            fill_value = kwargs.get('fillna_value', '')
            df = df.fillna(fill_value)
        
        # Remove duplicates if requested
        if kwargs.get('remove_duplicates', False):
            df = df.drop_duplicates()
        
        # Ensure all columns are CSV-safe (convert complex types to strings)
        for col in df.columns:
            dtype = df[col].dtype
            if dtype == 'object':
                # Check if it's a complex type
                sample = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
                if sample is not None and isinstance(sample, (dict, list)):
                    df[col] = df[col].astype(str)
        
        logger.info(f"Normalized to {len(df)} rows and {len(df.columns)} columns")
        return df
    
    @staticmethod
    def _clean_column_name(name: str) -> str:
        """Clean column name for CSV compatibility."""
        # Remove special characters, keep alphanumeric and underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        # Ensure it doesn't start with a number
        if cleaned and cleaned[0].isdigit():
            cleaned = 'col_' + cleaned
        # Ensure it's not empty
        if not cleaned:
            cleaned = 'unnamed_column'
        return cleaned


class DataValidator:
    """Agent 5: Validator Agent - Ensures data quality before CSV export"""
    
    @staticmethod
    def validate(df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Validate DataFrame quality.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'status': 'PASSED',
            'warnings': [],
            'errors': [],
            'stats': {}
        }
        
        # Check if DataFrame is empty
        if len(df) == 0:
            validation_results['status'] = 'FAILED'
            validation_results['errors'].append("DataFrame is empty")
            return validation_results
        
        # Check if DataFrame has columns
        if len(df.columns) == 0:
            validation_results['status'] = 'FAILED'
            validation_results['errors'].append("DataFrame has no columns")
            return validation_results
        
        # Check for required columns (if specified)
        required_cols = kwargs.get('required_columns', [])
        if required_cols:
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                validation_results['warnings'].append(f"Missing columns: {missing_cols}")
        
        # Calculate statistics
        validation_results['stats'] = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'null_percentage': (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100) if len(df) > 0 else 0,
            'duplicate_rows': df.duplicated().sum()
        }
        
        # Warn about high null percentage
        if validation_results['stats']['null_percentage'] > 50:
            validation_results['warnings'].append(f"High null percentage: {validation_results['stats']['null_percentage']:.2f}%")
        
        # Warn about duplicates
        if validation_results['stats']['duplicate_rows'] > 0:
            validation_results['warnings'].append(f"Found {validation_results['stats']['duplicate_rows']} duplicate rows")
        
        logger.info(f"Validation status: {validation_results['status']}")
        if validation_results['warnings']:
            logger.warning(f"Validation warnings: {validation_results['warnings']}")
        if validation_results['errors']:
            logger.error(f"Validation errors: {validation_results['errors']}")
        
        return validation_results


class UniversalDataIntakeAgent:
    """
    Universal Data Intake Agent
    
    Orchestrates all sub-agents to convert any data source to CSV format.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the Universal Data Intake Agent.
        
        Args:
            output_dir: Directory to save converted CSV files. Defaults to temp directory.
        """
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "data_intake"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.detector = DataFormatDetector()
        self.fetcher = DataFetcher()
        self.converter = DataConverter()
        self.normalizer = CSVNormalizer()
        self.validator = DataValidator()
    
    def process(
        self,
        data_source: Union[str, Path],
        output_filename: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process any data source and convert it to CSV.
        
        Args:
            data_source: Path to file, URL, or database connection string
            output_filename: Optional custom filename for output CSV
            **kwargs: Additional parameters for format-specific processing
        
        Returns:
            Dictionary with:
            - status: 'success' or 'error'
            - csv_path: Path to converted CSV file
            - format_detected: Detected format type
            - validation: Validation results
            - stats: Data statistics
        """
        try:
            # Step 1: Detect format
            format_type = self.detector.detect_format(data_source)
            logger.info(f"Detected format: {format_type}")
            
            # Step 2: Fetch data
            raw_data = self.fetcher.fetch(data_source, **kwargs)
            logger.info(f"Data fetched successfully")
            
            # Step 3: Convert to DataFrame
            df = self.converter.convert_to_dataframe(raw_data, format_type, **kwargs)
            logger.info(f"Converted to DataFrame: {df.shape}")
            
            # Step 4: Normalize
            df_normalized = self.normalizer.normalize(df, **kwargs)
            
            # Step 5: Validate
            validation = self.validator.validate(df_normalized, **kwargs)
            
            if validation['status'] == 'FAILED':
                return {
                    'status': 'error',
                    'error': 'Validation failed',
                    'validation': validation
                }
            
            # Step 6: Export to CSV
            if output_filename is None:
                source_name = Path(data_source).stem if isinstance(data_source, (str, Path)) else 'converted_data'
                output_filename = f"{source_name}_converted.csv"
            
            csv_path = self.output_dir / output_filename
            df_normalized.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"CSV exported to: {csv_path}")
            
            return {
                'status': 'success',
                'csv_path': str(csv_path),
                'format_detected': format_type,
                'validation': validation,
                'stats': {
                    'rows': len(df_normalized),
                    'columns': len(df_normalized.columns),
                    'file_size_mb': csv_path.stat().st_size / (1024 * 1024)
                }
            }
        
        except Exception as e:
            logger.error(f"Error processing data source: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'format_detected': format_type if 'format_type' in locals() else 'unknown'
            }
    
    def process_multiple(
        self,
        data_sources: List[Union[str, Path]],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process multiple data sources.
        
        Returns:
            List of processing results
        """
        results = []
        for source in data_sources:
            result = self.process(source, **kwargs)
            results.append(result)
        return results

