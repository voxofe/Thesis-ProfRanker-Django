import logging
import os

from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "phd-pdf").strip() or "phd-pdf"


def get_redis_connection():
	redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
	return Redis.from_url(redis_url)


def get_queue(name=None):
	queue_name = (name or DEFAULT_QUEUE_NAME).strip() or DEFAULT_QUEUE_NAME
	return Queue(queue_name, connection=get_redis_connection())


def enqueue_job(func, *args, **kwargs):
	queue = get_queue()
	return queue.enqueue(func, *args, **kwargs)


