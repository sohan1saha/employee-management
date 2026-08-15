"""
==============================================================================
StaffSync 360 - Prometheus & OpenTelemetry Observability Metrics Service
==============================================================================
Provides high-performance standard Prometheus metric exposition (/metrics)
including HTTP request latency histograms, status code counters, active DB
connections, and distributed cache performance metrics.
"""

import time
import threading
from typing import Dict, List, Tuple
from collections import defaultdict


class PrometheusMetricsCollector:
    """Thread-safe Prometheus Metric Collector conforming to OpenMetrics exposition standard."""

    def __init__(self):
        self._lock = threading.Lock()
        # Request Counters: (method, endpoint, status_code) -> count
        self.request_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)
        # Latency Buckets (seconds): [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.latency_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        # Latency Histogram: (method, endpoint) -> {le: count}
        self.request_latency_histogram: Dict[Tuple[str, str], Dict[float, int]] = defaultdict(
            lambda: {le: 0 for le in self.latency_buckets}
        )
        self.request_latency_sum: Dict[Tuple[str, str], float] = defaultdict(float)
        self.request_latency_count: Dict[Tuple[str, str], int] = defaultdict(int)
        # Cache Counters: (operation, status) -> count
        self.cache_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        # Process start timestamp
        self.start_time = time.time()

    def record_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float):
        """Record an incoming HTTP request with method, normalized endpoint, status, and latency."""
        with self._lock:
            self.request_counts[(method, endpoint, status_code)] += 1
            self.request_latency_count[(method, endpoint)] += 1
            self.request_latency_sum[(method, endpoint)] += duration_seconds

            hist = self.request_latency_histogram[(method, endpoint)]
            for le in self.latency_buckets:
                if duration_seconds <= le:
                    hist[le] += 1

    def record_cache_operation(self, operation: str, status: str):
        """Record a cache operation (e.g. 'get', 'hit' / 'miss' / 'error')."""
        with self._lock:
            self.cache_counts[(operation, status)] += 1

    def generate_prometheus_output(self, active_db_connections: int = 0) -> str:
        """Generate formatted Prometheus text exposition format (version 0.0.4)."""
        lines = []

        # System Uptime
        uptime = time.time() - self.start_time
        lines.append("# HELP process_uptime_seconds Total seconds elapsed since service startup.")
        lines.append("# TYPE process_uptime_seconds counter")
        lines.append(f"process_uptime_seconds {uptime:.2f}")

        # Active Database Connections
        lines.append("# HELP staffsync_db_active_connections Number of active database connections in pool.")
        lines.append("# TYPE staffsync_db_active_connections gauge")
        lines.append(f"staffsync_db_active_connections {active_db_connections}")

        # HTTP Requests Total
        lines.append("# HELP http_requests_total Total number of HTTP requests processed.")
        lines.append("# TYPE http_requests_total counter")
        with self._lock:
            for (method, endpoint, status_code), count in self.request_counts.items():
                lines.append(
                    f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status_code}"}} {count}'
                )

        # HTTP Request Duration Histogram
        lines.append("# HELP http_request_duration_seconds HTTP request latency histogram in seconds.")
        lines.append("# TYPE http_request_duration_seconds histogram")
        with self._lock:
            for (method, endpoint), hist in self.request_latency_histogram.items():
                for le in self.latency_buckets:
                    count = hist[le]
                    lines.append(
                        f'http_request_duration_seconds_bucket{{method="{method}",endpoint="{endpoint}",le="{le}"}} {count}'
                    )
                lines.append(
                    f'http_request_duration_seconds_bucket{{method="{method}",endpoint="{endpoint}",le="+Inf"}} {self.request_latency_count[(method, endpoint)]}'
                )
                lines.append(
                    f'http_request_duration_seconds_sum{{method="{method}",endpoint="{endpoint}"}} {self.request_latency_sum[(method, endpoint)]:.6f}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{method="{method}",endpoint="{endpoint}"}} {self.request_latency_count[(method, endpoint)]}'
                )

        # Cache Metrics
        lines.append("# HELP staffsync_cache_operations_total Total cache access operations.")
        lines.append("# TYPE staffsync_cache_operations_total counter")
        with self._lock:
            for (op, st), count in self.cache_counts.items():
                lines.append(f'staffsync_cache_operations_total{{operation="{op}",status="{st}"}} {count}')

        return "\n".join(lines) + "\n"


# Global metrics collector instance
metrics_collector = PrometheusMetricsCollector()
