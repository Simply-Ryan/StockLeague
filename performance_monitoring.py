"""
Performance Monitoring Module for StockLeague

Tracks and monitors:
- Real-time system metrics (CPU, memory, disk)
- API response times and latency
- Database performance
- Socket.IO connection health
- Error rates and slow endpoints

Provides dashboard data for /admin/performance endpoint.
"""

import psutil
import time
import logging
import threading
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Stores historical performance data with configurable window."""

    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics storage.
        
        Args:
            window_size: Max number of data points to keep per metric
        """
        self.window_size = window_size
        self.metrics = {
            'cpu_percent': deque(maxlen=window_size),
            'memory_percent': deque(maxlen=window_size),
            'memory_mb': deque(maxlen=window_size),
            'disk_percent': deque(maxlen=window_size),
            'api_latency': deque(maxlen=window_size),
            'db_latency': deque(maxlen=window_size),
            'error_count': deque(maxlen=window_size),
            'socket_connections': deque(maxlen=window_size),
        }
        self.timestamps = {key: deque(maxlen=window_size) for key in self.metrics.keys()}

    def add_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Add a metric value."""
        if metric_name in self.metrics:
            self.metrics[metric_name].append(value)
            self.timestamps[metric_name].append(timestamp or datetime.now())

    def get_latest(self, metric_name: str) -> Optional[float]:
        """Get latest metric value."""
        if metric_name in self.metrics and len(self.metrics[metric_name]) > 0:
            return self.metrics[metric_name][-1]
        return None

    def get_average(self, metric_name: str) -> float:
        """Get average metric value."""
        if metric_name in self.metrics and len(self.metrics[metric_name]) > 0:
            return sum(self.metrics[metric_name]) / len(self.metrics[metric_name])
        return 0.0

    def get_max(self, metric_name: str) -> float:
        """Get max metric value."""
        if metric_name in self.metrics and len(self.metrics[metric_name]) > 0:
            return max(self.metrics[metric_name])
        return 0.0

    def get_min(self, metric_name: str) -> float:
        """Get min metric value."""
        if metric_name in self.metrics and len(self.metrics[metric_name]) > 0:
            return min(self.metrics[metric_name])
        return 0.0

    def get_history(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get metric history."""
        if metric_name not in self.metrics:
            return []

        values = list(self.metrics[metric_name])[-limit:]
        times = list(self.timestamps[metric_name])[-limit:]

        return [
            {'value': val, 'timestamp': ts.isoformat()}
            for val, ts in zip(values, times)
        ]


class PerformanceMonitor:
    """
    Monitors and tracks performance metrics for the application.
    
    Collects:
    - System metrics (CPU, memory, disk)
    - API performance
    - Database performance
    - WebSocket metrics
    """

    def __init__(self, update_interval: float = 5.0):
        """
        Initialize performance monitor.
        
        Args:
            update_interval: Seconds between metric updates
        """
        self.update_interval = update_interval
        self.metrics = PerformanceMetrics()
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_thread = None
        self.alerts = deque(maxlen=100)
        self.alert_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'api_latency': 1000,  # milliseconds
            'db_latency': 500,
            'error_count': 10,  # per minute
        }

    def start_monitoring(self):
        """Start background monitoring thread."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop background monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.5)
            self.metrics.add_metric('cpu_percent', cpu_percent)
            if cpu_percent > self.alert_thresholds['cpu_percent']:
                self._create_alert('HIGH_CPU', f"CPU usage: {cpu_percent:.1f}%")

            # Memory usage
            mem_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            memory_mb = mem_info.rss / 1024 / 1024

            self.metrics.add_metric('memory_percent', memory_percent)
            self.metrics.add_metric('memory_mb', memory_mb)
            if memory_percent > self.alert_thresholds['memory_percent']:
                self._create_alert('HIGH_MEMORY', f"Memory usage: {memory_percent:.1f}% ({memory_mb:.1f}MB)")

            # Disk usage
            try:
                disk_usage = psutil.disk_usage('/')
                disk_percent = disk_usage.percent
                self.metrics.add_metric('disk_percent', disk_percent)
                if disk_percent > self.alert_thresholds['disk_percent']:
                    self._create_alert('HIGH_DISK', f"Disk usage: {disk_percent:.1f}%")
            except Exception as e:
                logger.debug(f"Could not get disk usage: {e}")

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def record_api_request(self, endpoint: str, duration_ms: float):
        """Record an API request's duration."""
        self.metrics.add_metric('api_latency', duration_ms)
        
        if duration_ms > self.alert_thresholds['api_latency']:
            self._create_alert('SLOW_API', f"Slow API: {endpoint} ({duration_ms:.0f}ms)")

    def record_db_query(self, query: str, duration_ms: float):
        """Record a database query's duration."""
        self.metrics.add_metric('db_latency', duration_ms)
        
        if duration_ms > self.alert_thresholds['db_latency']:
            self._create_alert('SLOW_DB', f"Slow query: {query[:50]}... ({duration_ms:.0f}ms)")

    def record_error(self):
        """Record an error occurrence."""
        current_count = self.metrics.get_latest('error_count') or 0
        self.metrics.add_metric('error_count', current_count + 1)

    def record_socket_connection(self, connected: bool):
        """Record WebSocket connection change."""
        current_count = self.metrics.get_latest('socket_connections') or 0
        new_count = current_count + (1 if connected else -1)
        self.metrics.add_metric('socket_connections', max(0, new_count))

    def _create_alert(self, alert_type: str, message: str):
        """Create a performance alert."""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'severity': self._get_severity(alert_type)
        }
        self.alerts.append(alert)
        logger.warning(f"Performance Alert [{alert_type}]: {message}")

    def _get_severity(self, alert_type: str) -> str:
        """Determine alert severity."""
        if alert_type.startswith('HIGH'):
            return 'critical'
        elif alert_type.startswith('SLOW'):
            return 'warning'
        return 'info'

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all metrics for dashboard display."""
        return {
            'system': {
                'cpu': {
                    'current': self.metrics.get_latest('cpu_percent'),
                    'average': self.metrics.get_average('cpu_percent'),
                    'max': self.metrics.get_max('cpu_percent'),
                    'threshold': self.alert_thresholds['cpu_percent']
                },
                'memory': {
                    'percent': self.metrics.get_latest('memory_percent'),
                    'mb': self.metrics.get_latest('memory_mb'),
                    'average_percent': self.metrics.get_average('memory_percent'),
                    'max_percent': self.metrics.get_max('memory_percent'),
                    'threshold': self.alert_thresholds['memory_percent']
                },
                'disk': {
                    'percent': self.metrics.get_latest('disk_percent'),
                    'threshold': self.alert_thresholds['disk_percent']
                }
            },
            'api': {
                'latency_ms': self.metrics.get_latest('api_latency'),
                'average_ms': self.metrics.get_average('api_latency'),
                'max_ms': self.metrics.get_max('api_latency'),
                'threshold': self.alert_thresholds['api_latency']
            },
            'database': {
                'latency_ms': self.metrics.get_latest('db_latency'),
                'average_ms': self.metrics.get_average('db_latency'),
                'max_ms': self.metrics.get_max('db_latency'),
                'threshold': self.alert_thresholds['db_latency']
            },
            'websocket': {
                'connections': self.metrics.get_latest('socket_connections') or 0
            },
            'alerts': list(self.alerts),
            'timestamp': datetime.now().isoformat()
        }

    def get_metrics_history(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        return self.metrics.get_history(metric_name, limit)

    def set_threshold(self, metric: str, threshold: float):
        """Update alert threshold for a metric."""
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = threshold
            logger.info(f"Updated {metric} threshold to {threshold}")


def monitor_endpoint(monitor: PerformanceMonitor):
    """
    Decorator to monitor API endpoint performance.
    
    Usage:
        @monitor_endpoint(performance_monitor)
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                monitor.record_error()
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                endpoint_name = f.__name__
                monitor.record_api_request(endpoint_name, duration_ms)

        return decorated_function
    return decorator
