"""
Scalability Components for 100GB+ Data Processing
Implements data engineering, storage, retrieval, and orchestration patterns
required for enterprise-scale deployment.
"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================================================
# A. DATA ENGINEERING - Ingestion & Preprocessing
# ============================================================================

class DataIngestionStrategy(ABC):
    """Abstract base for data ingestion strategies"""
    
    @abstractmethod
    def ingest(self, source: str, destination: str) -> Dict[str, Any]:
        """Ingest data from source to destination"""
        pass
    
    @abstractmethod
    def validate(self, data_path: str) -> bool:
        """Validate data quality"""
        pass


class LocalCSVIngestion(DataIngestionStrategy):
    """Current implementation - Local CSV files"""
    
    def ingest(self, source: str, destination: str) -> Dict[str, Any]:
        """Load CSV to DuckDB"""
        import duckdb
        import pandas as pd
        
        conn = duckdb.connect(destination)
        table_name = Path(source).stem.replace(' ', '_').replace('-', '_')
        
        try:
            # Load CSV with auto-detection
            conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS 
                SELECT * FROM read_csv_auto('{source}', 
                    header=True, 
                    ignore_errors=True,
                    sample_size=100000
                )
            """)
            
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            return {
                "status": "success",
                "table": table_name,
                "rows": count,
                "source": source
            }
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            conn.close()
    
    def validate(self, data_path: str) -> bool:
        """Check if CSV is valid"""
        try:
            import pandas as pd
            df = pd.read_csv(data_path, nrows=10)
            return len(df) > 0
        except:
            return False


class DaskDistributedIngestion(DataIngestionStrategy):
    """Scalable ingestion using Dask for 10GB+ files"""
    
    def __init__(self, n_workers: int = 4):
        self.n_workers = n_workers
    
    def ingest(self, source: str, destination: str) -> Dict[str, Any]:
        """Process large CSV files in parallel using Dask"""
        try:
            import dask.dataframe as dd
            
            # Read in chunks
            logger.info(f"Reading {source} with Dask ({self.n_workers} workers)")
            ddf = dd.read_csv(source, blocksize='64MB')
            
            # Data cleaning
            ddf = ddf.dropna(how='all')
            
            # Convert to Parquet (10x smaller, faster queries)
            parquet_path = destination.replace('.db', '.parquet')
            ddf.to_parquet(
                parquet_path,
                engine='pyarrow',
                compression='snappy',
                partition_on=['year', 'month'] if 'date' in ddf.columns else None
            )
            
            return {
                "status": "success",
                "format": "parquet",
                "path": parquet_path,
                "partitions": ddf.npartitions
            }
        except ImportError:
            logger.warning("Dask not installed. Install with: pip install dask[dataframe]")
            return {"status": "error", "error": "Dask not available"}
        except Exception as e:
            logger.error(f"Dask ingestion failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def validate(self, data_path: str) -> bool:
        """Validate parquet file"""
        try:
            import pyarrow.parquet as pq
            table = pq.read_table(data_path)
            return len(table) > 0
        except:
            return False


class SparkDistributedIngestion(DataIngestionStrategy):
    """Enterprise-scale ingestion using PySpark for 100GB+ datasets"""
    
    def __init__(self, spark_config: Optional[Dict] = None):
        self.config = spark_config or {
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true"
        }
    
    def ingest(self, source: str, destination: str) -> Dict[str, Any]:
        """Process massive datasets with Spark"""
        try:
            from pyspark.sql import SparkSession
            
            spark = SparkSession.builder \
                .appName("RetailDataIngestion") \
                .config("spark.driver.memory", "4g") \
                .getOrCreate()
            
            # Configure for optimizations
            for key, value in self.config.items():
                spark.conf.set(key, value)
            
            # Read CSV
            df = spark.read.csv(source, header=True, inferSchema=True)
            
            # Data quality checks
            df = df.dropna(how='all')
            df = df.dropDuplicates()
            
            # Write as Delta Lake (ACID transactions + time travel)
            delta_path = destination.replace('.db', '_delta')
            df.write.format("delta") \
                .mode("overwrite") \
                .partitionBy("year", "month") \
                .save(delta_path)
            
            return {
                "status": "success",
                "format": "delta",
                "path": delta_path,
                "row_count": df.count()
            }
        except ImportError:
            logger.warning("PySpark not installed. Install with: pip install pyspark")
            return {"status": "error", "error": "Spark not available"}
        except Exception as e:
            logger.error(f"Spark ingestion failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def validate(self, data_path: str) -> bool:
        """Validate Delta Lake table"""
        try:
            from delta import DeltaTable
            dt = DeltaTable.forPath(data_path)
            return dt is not None
        except:
            return False


# ============================================================================
# B. STORAGE & INDEXING - Cloud-ready storage strategies
# ============================================================================

class StorageStrategy(ABC):
    """Abstract storage backend"""
    
    @abstractmethod
    def save(self, data: Any, path: str) -> str:
        """Save data and return URI"""
        pass
    
    @abstractmethod
    def load(self, path: str) -> Any:
        """Load data from URI"""
        pass


class LocalStorage(StorageStrategy):
    """Current implementation - local filesystem"""
    
    def save(self, data: Any, path: str) -> str:
        if isinstance(data, bytes):
            with open(path, 'wb') as f:
                f.write(data)
        else:
            import pickle
            with open(path, 'wb') as f:
                pickle.dump(data, f)
        return f"file://{path}"
    
    def load(self, path: str) -> Any:
        import pickle
        with open(path, 'rb') as f:
            return pickle.load(f)


class S3Storage(StorageStrategy):
    """AWS S3 storage for cloud deployment"""
    
    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region
    
    def save(self, data: Any, path: str) -> str:
        try:
            import boto3
            s3 = boto3.client('s3', region_name=self.region)
            
            if isinstance(data, bytes):
                s3.put_object(Bucket=self.bucket, Key=path, Body=data)
            else:
                import pickle
                s3.put_object(Bucket=self.bucket, Key=path, Body=pickle.dumps(data))
            
            return f"s3://{self.bucket}/{path}"
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise
    
    def load(self, path: str) -> Any:
        import boto3
        import pickle
        s3 = boto3.client('s3', region_name=self.region)
        obj = s3.get_object(Bucket=self.bucket, Key=path)
        return pickle.loads(obj['Body'].read())


# ============================================================================
# C. RETRIEVAL - Efficient data loading strategies
# ============================================================================

class QueryOptimizer:
    """Optimize queries for large datasets"""
    
    @staticmethod
    def estimate_query_cost(query: str, table_stats: Dict) -> int:
        """Estimate rows that will be scanned"""
        # Simple heuristic - can be enhanced with query parsing
        if "LIMIT" in query.upper():
            import re
            match = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return table_stats.get('total_rows', 1000000)
    
    @staticmethod
    def should_use_cache(query: str, cost: int, cache_ttl: int = 3600) -> bool:
        """Determine if query result should be cached"""
        # Cache expensive queries (>10K rows) or aggregations
        if cost > 10000:
            return True
        if any(kw in query.upper() for kw in ['SUM', 'AVG', 'COUNT', 'GROUP BY']):
            return True
        return False
    
    @staticmethod
    def rewrite_for_performance(query: str) -> str:
        """Rewrite query for better performance"""
        # Add LIMIT if missing on large scans
        if 'LIMIT' not in query.upper() and 'GROUP BY' not in query.upper():
            query += " LIMIT 10000"
        return query


class MetadataFilter:
    """Filter data using metadata before full scan"""
    
    def __init__(self, metadata_store: Dict):
        self.metadata = metadata_store
    
    def filter_partitions(self, query: str) -> List[str]:
        """Return only relevant partitions to scan"""
        # Example: if query filters by date, only return matching partitions
        relevant_partitions = []
        
        # Parse query for date filters (simplified)
        if "WHERE" in query.upper():
            # In production, use proper SQL parser
            for partition, meta in self.metadata.items():
                if self._partition_matches(query, meta):
                    relevant_partitions.append(partition)
        
        return relevant_partitions or list(self.metadata.keys())
    
    def _partition_matches(self, query: str, metadata: Dict) -> bool:
        """Check if partition matches query filters"""
        # Simplified logic - enhance with proper query parsing
        return True  # Default: include all


# ============================================================================
# D. ORCHESTRATION - Workflow management & caching
# ============================================================================

class QueryCache:
    """In-memory and Redis-backed query result cache"""
    
    def __init__(self, backend: str = "memory", redis_url: Optional[str] = None):
        self.backend = backend
        self.memory_cache = {}
        
        if backend == "redis" and redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url)
            except ImportError:
                logger.warning("redis not installed. Using memory cache. Install: pip install redis")
                self.backend = "memory"
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result"""
        if self.backend == "memory":
            return self.memory_cache.get(key)
        else:
            try:
                import pickle
                data = self.redis_client.get(key)
                return pickle.loads(data) if data else None
            except:
                return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set cached result with TTL"""
        if self.backend == "memory":
            self.memory_cache[key] = value
        else:
            try:
                import pickle
                self.redis_client.setex(key, ttl, pickle.dumps(value))
            except Exception as e:
                logger.error(f"Cache set failed: {e}")
    
    def clear(self):
        """Clear all cached results"""
        if self.backend == "memory":
            self.memory_cache.clear()
        else:
            try:
                self.redis_client.flushdb()
            except:
                pass


class WorkflowOrchestrator:
    """Orchestrate multi-agent workflow with retry and fallback logic"""
    
    def __init__(self, cache: Optional[QueryCache] = None):
        self.cache = cache or QueryCache()
        self.metrics = {
            "queries_executed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
    
    def execute_with_cache(self, query: str, executor_fn, ttl: int = 3600) -> Any:
        """Execute query with caching"""
        import hashlib
        cache_key = hashlib.md5(query.encode()).hexdigest()
        
        # Try cache first
        result = self.cache.get(cache_key)
        if result is not None:
            self.metrics["cache_hits"] += 1
            logger.info(f"Cache HIT for query: {query[:50]}...")
            return result
        
        # Cache miss - execute
        self.metrics["cache_misses"] += 1
        self.metrics["queries_executed"] += 1
        logger.info(f"Cache MISS - executing: {query[:50]}...")
        
        try:
            result = executor_fn(query)
            self.cache.set(cache_key, result, ttl)
            return result
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        hit_rate = self.metrics["cache_hits"] / total if total > 0 else 0
        
        return {
            **self.metrics,
            "cache_hit_rate": f"{hit_rate*100:.1f}%",
            "total_requests": total
        }


# ============================================================================
# E. MONITORING - Cost & performance tracking
# ============================================================================

class PerformanceMonitor:
    """Monitor query performance and costs"""
    
    def __init__(self):
        self.query_log = []
        self.cost_per_model = {
            "gpt-4": 0.03,  # per 1K tokens input
            "gpt-3.5-turbo": 0.0015,
            "gemini-pro": 0.00025
        }
    
    def log_query(self, query: str, execution_time: float, tokens_used: int, model: str):
        """Log query execution"""
        self.query_log.append({
            "query": query,
            "execution_time": execution_time,
            "tokens": tokens_used,
            "model": model,
            "estimated_cost": (tokens_used / 1000) * self.cost_per_model.get(model, 0)
        })
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost breakdown"""
        total_cost = sum(q["estimated_cost"] for q in self.query_log)
        total_queries = len(self.query_log)
        avg_time = sum(q["execution_time"] for q in self.query_log) / total_queries if total_queries > 0 else 0
        
        return {
            "total_queries": total_queries,
            "total_cost_usd": f"${total_cost:.4f}",
            "avg_execution_time": f"{avg_time:.2f}s",
            "avg_cost_per_query": f"${total_cost/total_queries:.4f}" if total_queries > 0 else "$0"
        }
    
    def check_alert_thresholds(self, max_cost: float = 100.0, max_latency: float = 10.0) -> List[str]:
        """Check if any thresholds are exceeded"""
        alerts = []
        
        recent_queries = self.query_log[-100:] if len(self.query_log) > 100 else self.query_log
        total_cost = sum(q["estimated_cost"] for q in recent_queries)
        
        if total_cost > max_cost:
            alerts.append(f"ALERT: Cost threshold exceeded: ${total_cost:.2f} > ${max_cost}")
        
        slow_queries = [q for q in recent_queries if q["execution_time"] > max_latency]
        if slow_queries:
            alerts.append(f"ALERT: {len(slow_queries)} slow queries (>{max_latency}s)")
        
        return alerts


# ============================================================================
# FACTORY - Select appropriate strategy based on data size
# ============================================================================

class ScalabilityFactory:
    """Factory to select appropriate strategy based on data size"""
    
    @staticmethod
    def get_ingestion_strategy(data_size_gb: float) -> DataIngestionStrategy:
        """Select ingestion strategy based on data size"""
        if data_size_gb < 1:
            return LocalCSVIngestion()
        elif data_size_gb < 50:
            return DaskDistributedIngestion()
        else:
            return SparkDistributedIngestion()
    
    @staticmethod
    def get_storage_strategy(deployment: str = "local") -> StorageStrategy:
        """Select storage based on deployment environment"""
        if deployment == "aws":
            return S3Storage(bucket=os.getenv("S3_BUCKET", "retail-insights"))
        # Add GCS, Azure options here
        return LocalStorage()
    
    @staticmethod
    def get_cache_backend(deployment: str = "local") -> QueryCache:
        """Select cache backend"""
        if deployment in ["production", "aws", "gcp", "azure"]:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                return QueryCache(backend="redis", redis_url=redis_url)
        return QueryCache(backend="memory")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Auto-select strategy based on data size
    data_size = 0.5  # GB
    
    ingestion = ScalabilityFactory.get_ingestion_strategy(data_size)
    print(f"Selected ingestion strategy: {ingestion.__class__.__name__}")
    
    # Example: Use cache
    cache = ScalabilityFactory.get_cache_backend("local")
    orchestrator = WorkflowOrchestrator(cache)
    
    # Example: Monitor performance
    monitor = PerformanceMonitor()
    monitor.log_query("SELECT * FROM sales", 2.5, 1500, "gpt-3.5-turbo")
    print(monitor.get_cost_summary())
