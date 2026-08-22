from prometheus_client import Counter, Gauge, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "library_http_requests_total",
    "Total HTTP requests processed by the API",
    labelnames=["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "library_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ACTIVE_REQUESTS = Gauge(
    "library_active_requests",
    "Current number of in-flight HTTP requests",
)

CACHE_HITS = Counter(
    "library_cache_hits_total",
    "Redis cache hits by entity",
    labelnames=["entity"],
)

CACHE_MISSES = Counter(
    "library_cache_misses_total",
    "Redis cache misses by entity",
    labelnames=["entity"],
)

BOOKS_BORROWED = Counter(
    "library_books_borrowed_total",
    "Total successful borrow operations",
)

BOOKS_RETURNED = Counter(
    "library_books_returned_total",
    "Total successful return operations",
)

AUTH_EVENTS = Counter(
    "library_auth_events_total",
    "Authentication events by type and outcome",
    labelnames=["event_type", "outcome"],
)

ERRORS_TOTAL = Counter(
    "library_errors_total",
    "Application errors by type and endpoint",
    labelnames=["error_type", "endpoint"],
)
