"""Celery application configuration with priority queues and DLQ."""

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import get_settings

# Ensure all SQLAlchemy models are loaded (needed for FK resolution in workers)
import app.models  # noqa: F401

settings = get_settings()

app = Celery("meetscript")

# ── Broker + Result Backend ────────────────────────────────────────
redis_broker_url = f"{settings.REDIS_URL}/{settings.REDIS_BROKER_DB}"
redis_result_url = f"{settings.REDIS_URL}/{settings.REDIS_RESULT_DB}"

app.conf.broker_url = redis_broker_url
app.conf.result_backend = redis_result_url
app.conf.result_expires = 86400 * 7  # 7 days
app.conf.result_extended = True

# ── Serialization ──────────────────────────────────────────────────
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.timezone = "UTC"
app.conf.enable_utc = True

# ── Priority Queues ────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")

app.conf.task_queues = (
    Queue("priority_high", default_exchange, routing_key="priority.high"),
    Queue("priority_normal", default_exchange, routing_key="priority.normal"),
    Queue("priority_low", default_exchange, routing_key="priority.low"),
    Queue("dlq", default_exchange, routing_key="dlq"),  # Dead Letter Queue
)

app.conf.task_default_queue = "priority_normal"
app.conf.task_default_routing_key = "priority.normal"
app.conf.task_default_exchange = "default"
app.conf.task_default_exchange_type = "direct"

# ── Worker Settings ────────────────────────────────────────────────
app.conf.worker_prefetch_multiplier = 1  # Fair dispatch
app.conf.worker_max_tasks_per_child = 200  # Prevent memory leaks
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# ── Retry / Dead Letter ────────────────────────────────────────────
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

# ── Autodiscover Tasks ─────────────────────────────────────────────
app.autodiscover_tasks(
    [
        "app.tasks.process_meeting",
        "app.tasks.audio_task",
        "app.tasks.asr_task",
        "app.tasks.translation_task",
        "app.tasks.summary_task",
        "app.tasks.export_task",
    ],
    force=True,
)
