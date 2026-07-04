"""Middleware: Prometheus metrics collection."""

from prometheus_client import Counter, Gauge, Histogram

# ── Business Metrics ────────────────────────────────────────────────
celery_queue_depth = Gauge(
    "meetscript_celery_queue_depth",
    "Celery queue depth by queue name",
    ["queue_name"],
)

asr_duration_seconds = Histogram(
    "meetscript_asr_duration_seconds",
    "ASR processing duration in seconds",
    buckets=(30, 60, 120, 300, 600, 1800, 3600),
)

api_call_counter = Counter(
    "meetscript_api_calls_total",
    "Total AI API calls by model and operation",
    ["model", "operation"],
)

translation_cache_hits = Counter(
    "meetscript_translation_cache_hits_total",
    "Translation cache hit count",
)

dlq_task_count = Gauge(
    "meetscript_dlq_task_count",
    "Number of tasks currently in Dead Letter Queue",
)
