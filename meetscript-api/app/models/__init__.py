# Import all models to ensure they are registered in SQLAlchemy Base metadata.
# This is needed for Celery workers which import tasks but not all route handlers.

from app.models.user import User  # noqa: F401
from app.models.meeting import Meeting  # noqa: F401
from app.models.subtitle import Subtitle  # noqa: F401
from app.models.translation import Translation  # noqa: F401
from app.models.task import MeetingTask  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
from app.models.token_usage import TokenUsage  # noqa: F401
from app.models.model_config import ModelConfig  # noqa: F401