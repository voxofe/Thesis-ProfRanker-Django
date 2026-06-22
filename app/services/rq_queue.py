import logging
import os

from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "background").strip() or "background"


def parse_env_bool(value, default=False):
	if value is None:
		return default
	normalized = str(value).strip().lower()
	if normalized in {"1", "true", "yes", "on"}:
		return True
	if normalized in {"0", "false", "no", "off"}:
		return False
	return default


def is_rq_enabled():
	return parse_env_bool(os.getenv("RQ_ENABLED", "true"), True)


def get_redis_connection():
	redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
	return Redis.from_url(redis_url)


def get_queue(name=None):
	queue_name = (name or DEFAULT_QUEUE_NAME).strip() or DEFAULT_QUEUE_NAME
	return Queue(queue_name, connection=get_redis_connection())


def enqueue_job(func, *args, **kwargs):
	if not is_rq_enabled():
		raise RuntimeError("RQ is disabled (RQ_ENABLED=false).")
	queue = get_queue()
	return queue.enqueue(func, *args, **kwargs)


