import os
import logging
from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)


def get_redis_url():
    return os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()


def get_queue(name="phd-pdf"):
    redis_url = get_redis_url()
    connection = Redis.from_url(redis_url)
    return Queue(name, connection=connection)


def enqueue_phd_pdf(document_id):
    from app.services.phd_pdf import process_phd_pdf

    try:
        queue = get_queue()
        job = queue.enqueue(process_phd_pdf, document_id)
        logger.info("Enqueued PhD PDF processing job %s for document %s", job.id, document_id)
        return job.id
    except Exception as exc:
        logger.exception("Failed to enqueue PhD PDF processing job: %s", exc)
        return None


def enqueue_phd_check(check_id):
    from app.services.phd_pdf import process_phd_check

    try:
        queue = get_queue()
        job = queue.enqueue(process_phd_check, check_id)
        logger.info("Enqueued PhD check job %s for check %s", job.id, check_id)
        return job.id
    except Exception as exc:
        logger.exception("Failed to enqueue PhD check job: %s", exc)
        return None


