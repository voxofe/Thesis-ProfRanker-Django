from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from django.utils import timezone

from app.models import Application, Position
from app.utils.email_utils import send_template_batch_email


def process_position_closed_emails():
    tz = ZoneInfo("Europe/Athens")
    now = timezone.now().astimezone(tz)

    positions = (
        Position.objects.filter(end_date__lte=now.date(), closed_notified_at__isnull=True)
        .select_related("scientific_field")
        .order_by("end_date", "end_time", "id")
    )

    sent_positions = 0
    sent_emails = 0
    skipped_positions = 0

    def chunked(items, size):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    for position in positions:
        end_time = position.end_time or dt_time(23, 59)
        end_dt = datetime.combine(position.end_date, end_time, tzinfo=tz)
        if end_dt > now:
            skipped_positions += 1
            continue

        applicants = Application.objects.filter(position=position).select_related("user")
        emails = sorted({app.user.email for app in applicants if app.user and app.user.email})
        if emails:
            context = {
                "scientific_field": position.scientific_field.name,
            }
            try:
                for batch in chunked(emails, 100):
                    send_template_batch_email("position_closed", batch, context)
                    sent_emails += len(batch)
            except Exception as exc:
                print(f"Position closed email failed ({position.id}): {exc}")
                continue

        position.closed_notified_at = timezone.now()
        position.save(update_fields=["closed_notified_at"])
        sent_positions += 1

    return {
        "positions_processed": sent_positions,
        "positions_skipped": skipped_positions,
        "emails_sent": sent_emails,
    }


def send_position_closed_emails_job():
    return process_position_closed_emails()
