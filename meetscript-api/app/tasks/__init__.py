"""Celery async tasks for MeetScript."""

from app.core.celery_app import app as celery_app

__all__ = ["celery_app"]
