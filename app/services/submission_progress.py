from django.core.cache import cache
from django.utils import timezone

SUBMISSION_PROGRESS_TTL_SECONDS = 15 * 60


def submission_progress_key(submission_id):
    return f"submission_progress:{submission_id}"


def get_submission_progress(submission_id):
    if not submission_id:
        return None
    return cache.get(submission_progress_key(submission_id))


def set_submission_progress(
    submission_id,
    user_id,
    percent,
    label,
    detail=None,
    done=False,
    error=None,
):
    if not submission_id:
        return None
    payload = {
        "userId": user_id,
        "percent": int(percent),
        "label": label,
        "detail": detail,
        "done": bool(done),
        "error": error,
        "updatedAt": timezone.now().isoformat(),
    }
    cache.set(submission_progress_key(submission_id), payload, SUBMISSION_PROGRESS_TTL_SECONDS)
    return payload


def set_submission_progress_safe(
    submission_id,
    user_id,
    percent,
    label,
    detail=None,
    done=False,
    error=None,
):
    existing = get_submission_progress(submission_id)
    if existing is not None:
        try:
            if int(existing.get("percent", 0)) >= int(percent):
                return existing
        except (TypeError, ValueError):
            pass
    return set_submission_progress(
        submission_id,
        user_id,
        percent,
        label,
        detail=detail,
        done=done,
        error=error,
    )
