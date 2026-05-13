import os
import threading

import requests
from django.conf import settings

from .email_templates import build_email_payload


def build_email_html(subject, body_html, headline=None, logo_url=None, footer_text=None):
    template_path = getattr(settings, "RESEND_EMAIL_TEMPLATE_PATH", "")
    if not template_path or not os.path.exists(template_path):
        raise FileNotFoundError("Email template not found.")

    with open(template_path, "r", encoding="utf-8") as handle:
        template = handle.read()

    return template.format(
        subject=subject,
        headline=headline or subject,
        body_html=body_html,
        logo_url=logo_url or getattr(settings, "RESEND_EMAIL_LOGO_URL", ""),
        footer_text=footer_text or getattr(settings, "RESEND_EMAIL_FOOTER", ""),
    )


def send_resend_email(to_email, subject, html, text=None, from_email=None):
    api_key = getattr(settings, "RESEND_API_KEY", "") or ""
    if not api_key:
        raise ValueError("RESEND_API_KEY is not configured.")

    sender = from_email or getattr(settings, "RESEND_FROM_EMAIL", "") or ""
    if not sender:
        raise ValueError("RESEND_FROM_EMAIL is not configured.")

    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    response = requests.post(
        getattr(settings, "RESEND_API_URL", "https://api.resend.com/emails"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )

    try:
        data = response.json()
    except ValueError:
        data = {"error": response.text}

    if not response.ok:
        message = data.get("error") if isinstance(data, dict) else None
        raise RuntimeError(message or "Resend API request failed.")

    return data


def _get_resend_batch_url():
    base_url = getattr(settings, "RESEND_API_URL", "https://api.resend.com/emails")
    if base_url.endswith("/emails"):
        return f"{base_url}/batch"
    return f"{base_url.rstrip('/')}/emails/batch"


def send_resend_batch_emails(email_payloads, from_email=None):
    api_key = getattr(settings, "RESEND_API_KEY", "") or ""
    if not api_key:
        raise ValueError("RESEND_API_KEY is not configured.")

    sender = from_email or getattr(settings, "RESEND_FROM_EMAIL", "") or ""
    if not sender:
        raise ValueError("RESEND_FROM_EMAIL is not configured.")

    payload = []
    for item in email_payloads:
        email_item = {
            "from": sender,
            "to": item["to"],
            "subject": item["subject"],
            "html": item["html"],
        }
        if item.get("text"):
            email_item["text"] = item["text"]
        payload.append(email_item)

    response = requests.post(
        _get_resend_batch_url(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )

    try:
        data = response.json()
    except ValueError:
        data = {"error": response.text}

    if not response.ok:
        message = data.get("error") if isinstance(data, dict) else None
        raise RuntimeError(message or "Resend batch request failed.")

    return data


def send_resend_email_async(to_email, subject, html, text=None, from_email=None):
    def _worker():
        try:
            send_resend_email(
                to_email=to_email,
                subject=subject,
                html=html,
                text=text,
                from_email=from_email,
            )
        except Exception as exc:
            print(f"Async email failed: {exc}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread


def send_template_email_async(template_key, to_email, context=None):
    subject, headline, body_html, text = build_email_payload(template_key, context)
    html = build_email_html(subject=subject, headline=headline, body_html=body_html)
    return send_resend_email_async(to_email=to_email, subject=subject, html=html, text=text)


def send_template_email(template_key, to_email, context=None):
    subject, headline, body_html, text = build_email_payload(template_key, context)
    html = build_email_html(subject=subject, headline=headline, body_html=body_html)
    return send_resend_email(to_email=to_email, subject=subject, html=html, text=text)


def send_template_batch_email(template_key, to_emails, context=None):
    subject, headline, body_html, text = build_email_payload(template_key, context)
    html = build_email_html(subject=subject, headline=headline, body_html=body_html)
    payloads = [
        {"to": [email], "subject": subject, "html": html, "text": text}
        for email in to_emails
    ]
    if not payloads:
        return {"message": "No recipients"}
    return send_resend_batch_emails(payloads)
