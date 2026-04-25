"""
VYUHA Monitoring and Logging System
Provides structured logging, metrics collection, and health monitoring
"""

import logging
import json
import time
import functools
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response
from contextvars import ContextVar
import os

# Context variable for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# Configure structured logging
class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': request_id_var.get(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(log_level: str = None) -> logging.Logger:
    """
    Setup structured logging for the application
    """
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    
    # Create logger
    logger = logging.getLogger('vyuha')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Use JSON formatter in production, simple formatter in development
    if os.getenv('ENVIRONMENT') == 'production':
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for production
    if os.getenv('LOG_FILE'):
        file_handler = logging.FileHandler(os.getenv('LOG_FILE'))
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    return logger


# Initialize logger
logger = setup_logging()


class MetricsCollector:
    """
    Simple in-memory metrics collector
    For production, consider using Prometheus or similar
    """
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            'requests_total': 0,
            'requests_by_endpoint': {},
            'requests_by_status': {},
            'response_times': [],
            'errors_total': 0,
            'errors_by_type': {},
            'db_queries_total': 0,
            'db_query_times': [],
            'active_users': set(),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def record_request(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Record an API request"""
        self.metrics['requests_total'] += 1
        
        # By endpoint
        key = f"{method}:{endpoint}"
        self.metrics['requests_by_endpoint'][key] = \
            self.metrics['requests_by_endpoint'].get(key, 0) + 1
        
        # By status code
        status_key = str(status_code)
        self.metrics['requests_by_status'][status_key] = \
            self.metrics['requests_by_status'].get(status_key, 0) + 1
        
        # Response time (keep last 1000)
        self.metrics['response_times'].append(duration_ms)
        if len(self.metrics['response_times']) > 1000:
            self.metrics['response_times'] = self.metrics['response_times'][-1000:]
        
        self.metrics['last_updated'] = datetime.utcnow().isoformat()
    
    def record_error(self, error_type: str, endpoint: str):
        """Record an error"""
        self.metrics['errors_total'] += 1
        key = f"{error_type}:{endpoint}"
        self.metrics['errors_by_type'][key] = \
            self.metrics['errors_by_type'].get(key, 0) + 1
        self.metrics['last_updated'] = datetime.utcnow().isoformat()
    
    def record_db_query(self, duration_ms: float):
        """Record a database query"""
        self.metrics['db_queries_total'] += 1
        self.metrics['db_query_times'].append(duration_ms)
        if len(self.metrics['db_query_times']) > 1000:
            self.metrics['db_query_times'] = self.metrics['db_query_times'][-1000:]
        self.metrics['last_updated'] = datetime.utcnow().isoformat()
    
    def record_user_activity(self, user_id: str):
        """Record user activity"""
        self.metrics['active_users'].add(user_id)
        self.metrics['last_updated'] = datetime.utcnow().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics statistics"""
        stats = self.metrics.copy()
        
        # Calculate averages
        if self.metrics['response_times']:
            stats['avg_response_time_ms'] = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
            stats['max_response_time_ms'] = max(self.metrics['response_times'])
            stats['min_response_time_ms'] = min(self.metrics['response_times'])
        
        if self.metrics['db_query_times']:
            stats['avg_db_query_time_ms'] = sum(self.metrics['db_query_times']) / len(self.metrics['db_query_times'])
        
        stats['active_users_count'] = len(self.metrics['active_users'])
        
        # Don't expose raw lists in API
        del stats['response_times']
        del stats['db_query_times']
        del stats['active_users']
        
        return stats


# Global metrics collector
metrics = MetricsCollector()


async def log_request_middleware(request: Request, call_next):
    """
    Middleware to log all requests and collect metrics
    """
    # Generate request ID
    import uuid
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    # Start timing
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={'extra_data': {
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params),
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
        }}
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        # Log response
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
            extra={'extra_data': {
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
            }}
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response
        
    except Exception as e:
        # Calculate duration even on error
        duration_ms = (time.time() - start_time) * 1000
        
        # Record error metrics
        metrics.record_error(
            error_type=type(e).__name__,
            endpoint=request.url.path
        )
        
        # Log error
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)}",
            extra={'extra_data': {
                'method': request.method,
                'path': request.url.path,
                'error_type': type(e).__name__,
                'duration_ms': duration_ms,
            }},
            exc_info=True
        )
        
        raise


def log_action(action: str, user_id: Optional[str] = None, details: Optional[Dict] = None):
    """
    Log a user action for audit purposes
    """
    log_data = {
        'action': action,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
        'request_id': request_id_var.get(),
    }
    
    if details:
        log_data['details'] = details
    
    logger.info(f"User action: {action}", extra={'extra_data': log_data})


def timed(func: Callable) -> Callable:
    """
    Decorator to time function execution
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Function {func.__name__} completed in {duration_ms:.2f}ms",
                extra={'extra_data': {
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                }}
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Function {func.__name__} failed after {duration_ms:.2f}ms: {str(e)}",
                extra={'extra_data': {
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'error': str(e),
                }},
                exc_info=True
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Function {func.__name__} completed in {duration_ms:.2f}ms",
                extra={'extra_data': {
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                }}
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Function {func.__name__} failed after {duration_ms:.2f}ms: {str(e)}",
                extra={'extra_data': {
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'error': str(e),
                }},
                exc_info=True
            )
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


import asyncio


class HealthChecker:
    """
    Health check system for monitoring service status
    """
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                check_status = 'pass'
                if isinstance(result, dict):
                    result_state = str(result.get('status', '')).lower()
                    if result_state in ('error', 'fail', 'unhealthy'):
                        check_status = 'fail'

                results['checks'][name] = {
                    'status': check_status,
                    'details': result
                }
                if check_status == 'fail':
                    results['status'] = 'unhealthy'
            except Exception as e:
                results['checks'][name] = {
                    'status': 'fail',
                    'error': str(e)
                }
                results['status'] = 'unhealthy'
        
        return results


# Global health checker
health_checker = HealthChecker()

# Register default health checks
def register_default_health_checks():
    """Register default health checks for production"""
    from database import supabase
    
    def check_database():
        """Check if database is accessible"""
        try:
            if supabase:
                result = supabase.table("colleges").select("id").limit(1).execute()
                return {"status": "ok", "message": "Database connection successful"}
            return {"status": "error", "message": "Database not initialized"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_supabase_connection():
        """Check Supabase connectivity"""
        try:
            if supabase:
                result = supabase.from_("colleges").select("count").execute()
                return {"status": "ok", "message": "Supabase accessible"}
            return {"status": "error", "message": "Supabase client not initialized"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    health_checker.register_check("database", check_database)
    health_checker.register_check("supabase", check_supabase_connection)

# Auto-register on import
register_default_health_checks()

def get_logger():
    """Get the configured logger"""
    return logger


def get_metrics():
    """Get the metrics collector"""
    return metrics
