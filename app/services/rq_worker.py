import os
import sys
import django
from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    redis_conn = Redis.from_url(redis_url)

    queue_name = os.getenv("RQ_QUEUE_NAME", "background").strip() or "background"
    queue = Queue(queue_name, connection=redis_conn)
    # SimpleWorker avoids os.fork, which is not available on Windows.
    worker = SimpleWorker([queue], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
