from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ("method", "path", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)
JOBS_PROCESSED = Counter("document_jobs_processed_total", "Document jobs processed", ("status",))
JOB_DURATION = Histogram("document_job_duration_seconds", "Document processing duration")
