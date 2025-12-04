import pandas as pd
import duckdb
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging
from .config import DATA_PATH, DATA_FILES, DUCKDB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetailDataProcessor:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DUCKDB_PATH
        self.conn = duckdb.connect(str(self.db_path))
        self.data_path = DATA_PATH
        self.tables_loaded = False
        
    def load_data(self) -> Dict[str, Any]:
        stats = {}
        
        try:
            amazon_path = self.data_path / DATA_FILES['amazon_sales']
            if amazon_path.exists():
                logger.info(f"Loading {amazon_path}...")
                self.conn.execute(f"""
                    CREATE OR REPLACE TABLE amazon_sales AS 
                    SELECT * FROM read_csv_auto('{amazon_path}', header=True, ignore_errors=True)
                """)
                stats['amazon_sales'] = self.conn.execute("SELECT COUNT(*) FROM amazon_sales").fetchone()[0]
            
            sale_path = self.data_path / DATA_FILES['sale_report']
            if sale_path.exists():
                logger.info(f"Loading {sale_path}...")
                self.conn.execute(f"""
                    CREATE OR REPLACE TABLE inventory AS 
                    SELECT * FROM read_csv_auto('{sale_path}', header=True, ignore_errors=True)
                """)
                stats['inventory'] = self.conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
            
            intl_path = self.data_path / DATA_FILES['international_sales']
            if intl_path.exists():
                logger.info(f"Loading {intl_path}...")
                self.conn.execute(f"""
                    CREATE OR REPLACE TABLE international_sales AS 
                    SELECT * FROM read_csv_auto('{intl_path}', header=True, ignore_errors=True)
                """)
                stats['international_sales'] = self.conn.execute("SELECT COUNT(*) FROM international_sales").fetchone()[0]
            
            may_path = self.data_path / DATA_FILES['may_2022']
            if may_path.exists():
                self.conn.execute(f"""
                    CREATE OR REPLACE TABLE may_2022 AS 
                    SELECT * FROM read_csv_auto('{may_path}', header=True, ignore_errors=True)
                """)
                stats['may_2022'] = self.conn.execute("SELECT COUNT(*) FROM may_2022").fetchone()[0]
            
            pl_path = self.data_path / DATA_FILES['pl_march_2021']
            if pl_path.exists():
                self.conn.execute(f"""
                    CREATE OR REPLACE TABLE pl_march_2021 AS 
                    SELECT * FROM read_csv_auto('{pl_path}', header=True, ignore_errors=True)
                """)
                stats['pl_march_2021'] = self.conn.execute("SELECT COUNT(*) FROM pl_march_2021").fetchone()[0]
            
            self.tables_loaded = True
            logger.info("All data loaded successfully!")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
        
        return stats
    
    def execute_query(self, query: str) -> pd.DataFrame:
        try:
            result = self.conn.execute(query).fetchdf()
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def get_schema_info(self) -> Dict[str, List[str]]:
        schema_info = {}
        try:
            tables = self.conn.execute("SHOW TABLES").fetchall()
            for table in tables:
                table_name = table[0]
                columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
                schema_info[table_name] = [col[0] for col in columns]
        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            raise
        return schema_info
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        summary = {}
        
        try:
            if not self.tables_loaded:
                self.load_data()
            
            # Amazon Sales - simple queries on numeric data
            try:
                amazon_stats = self.conn.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        COUNT(DISTINCT "Order ID") as unique_orders,
                        COALESCE(SUM(Amount), 0) as total_revenue,
                        COALESCE(AVG(Amount), 0) as avg_order_value,
                        COUNT(DISTINCT Category) as unique_categories,
                        COUNT(DISTINCT "ship-state") as unique_states
                    FROM amazon_sales
                    WHERE Amount IS NOT NULL
                """).fetchone()
                
                if amazon_stats:
                    summary['amazon_sales'] = {
                        'total_orders': amazon_stats[0] or 0,
                        'unique_orders': amazon_stats[1] or 0,
                        'total_revenue': round(float(amazon_stats[2] or 0), 2),
                        'avg_order_value': round(float(amazon_stats[3] or 0), 2),
                        'unique_categories': amazon_stats[4] or 0,
                        'unique_states': amazon_stats[5] or 0
                    }
                else:
                    summary['amazon_sales'] = {
                        'total_orders': 0, 'unique_orders': 0, 'total_revenue': 0,
                        'avg_order_value': 0, 'unique_categories': 0, 'unique_states': 0
                    }
            except Exception as e:
                logger.warning(f"Could not get amazon_sales stats: {e}")
                summary['amazon_sales'] = {
                    'total_orders': 0, 'unique_orders': 0, 'total_revenue': 0,
                    'avg_order_value': 0, 'unique_categories': 0, 'unique_states': 0
                }
            
            # Top Categories
            try:
                top_categories = self.conn.execute("""
                    SELECT 
                        Category,
                        COUNT(*) as order_count,
                        COALESCE(SUM(Amount), 0) as revenue
                    FROM amazon_sales
                    WHERE Category IS NOT NULL AND Amount IS NOT NULL
                    GROUP BY Category
                    ORDER BY revenue DESC
                    LIMIT 5
                """).fetchdf()
                summary['top_categories'] = top_categories.to_dict('records') if len(top_categories) > 0 else []
            except:
                summary['top_categories'] = []
            
            # Top States
            try:
                top_states = self.conn.execute("""
                    SELECT 
                        "ship-state" as state,
                        COUNT(*) as order_count,
                        COALESCE(SUM(Amount), 0) as revenue
                    FROM amazon_sales
                    WHERE "ship-state" IS NOT NULL AND Amount IS NOT NULL
                    GROUP BY "ship-state"
                    ORDER BY revenue DESC
                    LIMIT 10
                """).fetchdf()
                summary['top_states'] = top_states.to_dict('records') if len(top_states) > 0 else []
            except:
                summary['top_states'] = []
            
            # Status Distribution
            try:
                status_dist = self.conn.execute("""
                    SELECT 
                        Status,
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM amazon_sales), 2) as percentage
                    FROM amazon_sales
                    WHERE Status IS NOT NULL
                    GROUP BY Status
                    ORDER BY count DESC
                """).fetchdf()
                summary['status_distribution'] = status_dist.to_dict('records') if len(status_dist) > 0 else []
            except:
                summary['status_distribution'] = []
            
            # International Sales
            try:
                intl_stats = self.conn.execute("""
                    SELECT 
                        COUNT(*) as total_transactions,
                        COALESCE(SUM(PCS), 0) as total_pieces,
                        COALESCE(SUM("GROSS AMT"), 0) as total_revenue,
                        COUNT(DISTINCT CUSTOMER) as unique_customers
                    FROM international_sales
                """).fetchone()
                
                summary['international_sales'] = {
                    'total_transactions': intl_stats[0],
                    'total_pieces': int(intl_stats[1]) if intl_stats[1] else 0,
                    'total_revenue': round(float(intl_stats[2]), 2) if intl_stats[2] else 0,
                    'unique_customers': intl_stats[3]
                }
            except:
                summary['international_sales'] = {'total_transactions': 0, 'total_pieces': 0, 'total_revenue': 0, 'unique_customers': 0}
            
            # Inventory
            try:
                inventory_stats = self.conn.execute("""
                    SELECT 
                        COUNT(*) as total_skus,
                        COALESCE(SUM(Stock), 0) as total_stock,
                        COUNT(DISTINCT Category) as unique_categories,
                        COUNT(DISTINCT Color) as unique_colors
                    FROM inventory
                """).fetchone()
                
                summary['inventory'] = {
                    'total_skus': inventory_stats[0],
                    'total_stock': int(inventory_stats[1]) if inventory_stats[1] else 0,
                    'unique_categories': inventory_stats[2],
                    'unique_colors': inventory_stats[3]
                }
            except:
                summary['inventory'] = {'total_skus': 0, 'total_stock': 0, 'unique_categories': 0, 'unique_colors': 0}
            
        except Exception as e:
            logger.error(f"Error generating summary statistics: {e}")
            raise
        
        return summary
    
    def load_csv_from_intake_agent(
        self,
        csv_path: Union[str, Path],
        table_name: Optional[str] = None,
        replace_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Load a CSV file converted by the Universal Data Intake Agent into DuckDB.
        
        This method allows the existing pipeline to work with any data source
        that has been converted to CSV by the Universal Data Intake Agent.
        
        Args:
            csv_path: Path to the CSV file (from Universal Data Intake Agent)
            table_name: Optional custom table name. If None, uses filename stem
            replace_existing: Whether to replace existing table if it exists
        
        Returns:
            Dictionary with loading statistics
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        if table_name is None:
            # Generate table name from filename
            table_name = csv_path.stem.replace(' ', '_').replace('-', '_').lower()
            # Remove common suffixes
            table_name = table_name.replace('_converted', '').replace('_converted_data', '')
        
        # Sanitize table name for SQL
        table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
        if table_name[0].isdigit():
            table_name = 'table_' + table_name
        
        try:
            action = "CREATE OR REPLACE TABLE" if replace_existing else "CREATE TABLE IF NOT EXISTS"
            
            logger.info(f"Loading CSV from intake agent: {csv_path} -> table: {table_name}")
            self.conn.execute(f"""
                {action} {table_name} AS 
                SELECT * FROM read_csv_auto('{csv_path}', header=True, ignore_errors=True)
            """)
            
            row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            logger.info(f"Successfully loaded {row_count} rows into table '{table_name}'")
            
            return {
                'status': 'success',
                'table_name': table_name,
                'row_count': row_count,
                'csv_path': str(csv_path)
            }
        except Exception as e:
            logger.error(f"Error loading CSV from intake agent: {e}")
            raise
    
    def search_data(self, search_term: str, limit: int = 100) -> pd.DataFrame:
        try:
            query = f"""
                SELECT 
                    'amazon_sales' as source,
                    "Order ID" as identifier,
                    Date,
                    Category,
                    Amount,
                    Status
                FROM amazon_sales
                WHERE 
                    LOWER(COALESCE(Category, '')) LIKE LOWER('%{search_term}%')
                    OR LOWER(COALESCE(Status, '')) LIKE LOWER('%{search_term}%')
                    OR LOWER(COALESCE("ship-state", '')) LIKE LOWER('%{search_term}%')
                LIMIT {limit}
            """
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Error searching data: {e}")
            return pd.DataFrame()
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        try:
            self.close()
        except:
            pass