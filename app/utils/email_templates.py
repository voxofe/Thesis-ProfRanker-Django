from html import escape
from django.conf import settings


def _frontend_base_url():
    return (getattr(settings, "FRONTEND_BASE_URL", "") or "http://localhost:3000").rstrip("/")


def _frontend_url(path):
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{_frontend_base_url()}{path}"


def build_guest_registration_email(context=None):
    context = context or {}
    verify_url = escape(context.get("verify_url", ""))
    has_verify_url = bool(verify_url)
    cta_html = (
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{verify_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Επιβεβαίωση email"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    ) if has_verify_url else ""
    subject = "Επιβεβαίωση εγγραφής στο ProfRanker"
    headline = (
        "Καλώς ήρθατε στο ProfRanker, την εφαρμογή αυτόματης αξιολόγησης "
        "υποψηφίων καθηγητών του Πανεπιστημίου Πατρών!"
    )
    if has_verify_url:
        body_html = (
            "<p>Η εγγραφή σας ολοκληρώθηκε με επιτυχία. Για να ενεργοποιήσετε τον λογαριασμό σας "
            "και να αποκτήσετε πρόσβαση σε όλες τις λειτουργίες, παρακαλώ επιβεβαιώστε το email σας.</p>"
            f"{cta_html}"
        )
        text = (
            "Η εγγραφή σας ολοκληρώθηκε με επιτυχία. Για να ενεργοποιήσετε τον λογαριασμό σας "
            "και να αποκτήσετε πρόσβαση σε όλες τις λειτουργίες, παρακαλώ επιβεβαιώστε το email σας. "
            f"Επιβεβαίωση: {verify_url}"
        )
    else:
        body_html = "<p>Η εγγραφή σας ολοκληρώθηκε με επιτυχία. Μπορείτε να συνδεθείτε και να χρησιμοποιήσετε την εφαρμογή.</p>"
        text = "Η εγγραφή σας ολοκληρώθηκε με επιτυχία. Μπορείτε να συνδεθείτε και να χρησιμοποιήσετε την εφαρμογή."
    return subject, headline, body_html, text


def build_admin_registration_email(context=None):
    context = context or {}
    login_url = escape(context.get("login_url") or _frontend_url("/login"))
    creator_first_name = escape(str(context.get("creator_first_name", "") or ""))
    creator_last_name = escape(str(context.get("creator_last_name", "") or ""))
    creator_email = escape(str(context.get("creator_email", "") or ""))
    username = escape(str(context.get("username", "") or ""))
    password = escape(str(context.get("password", "") or ""))

    creator_identity = ""
    if creator_first_name or creator_last_name or creator_email:
        full_name = " ".join(part for part in [creator_first_name, creator_last_name] if part).strip()
        if full_name and creator_email:
            creator_identity = f"{full_name} ({creator_email})"
        else:
            creator_identity = full_name or creator_email

    credentials_html = ""
    if username or password:
        credentials_html = (
            "<p><strong>Στοιχεία σύνδεσης:</strong></p>"
            "<ul style=\"margin:0 0 16px 18px;padding:0;\">"
            "<li>Το email αυτό</li>"
            f"<li>Κωδικός πρόσβασης: <strong>{password}</strong>.</li>"
            "</ul>"
        )

    creator_html = ""
    if creator_identity:
        creator_html = (
            "<p>Ο λογαριασμός διαχειριστή σας δημιουργήθηκε από τον διαχειριστή "
            f"<strong>{creator_identity}</strong>."
            " Παρακάτω θα βρείτε το όνομα χρήστη και τον κωδικό πρόσβασης με τα οποία μπορείτε να "
            "συνδεθείτε και να διαχειριστείτε αιτήσεις, θέσεις, επιστημονικά πεδία κ.α.</p>"
        )

    cta_html = (
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{login_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Σύνδεση και αλλαγή κωδικού"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    subject = "Επιβεβαίωση εγγραφής ως διαχειριστής στο ProfRanker"
    headline = (
        "Καλώς ήρθατε ως διαχειριστής στο ProfRanker, την εφαρμογή αυτόματης "
        "αξιολόγησης υποψηφίων καθηγητών του Πανεπιστημίου Πατρών!"
    )
    body_html = (
        f"{creator_html}"
        f"{credentials_html}"
        "<p><strong>Σημαντικό:</strong> Επειδή ο αρχικός κωδικός ορίστηκε από άλλον διαχειριστή, "
        "στην πρώτη σύνδεση θα σας ζητηθεί υποχρεωτικά να τον αλλάξετε πριν συνεχίσετε.</p>"
        f"{cta_html}"
    )
    text = (
        "Ο λογαριασμός διαχειριστή σας δημιουργήθηκε. "
        f"Δημιουργία από: {creator_identity}. "
        f"Στοιχεία σύνδεσης: - Το email αυτό - Κωδικός πρόσβασης: {password}. "
        "Σημαντικό: Στην πρώτη σύνδεση θα σας ζητηθεί υποχρεωτικά αλλαγή κωδικού. "
        f"Σύνδεση: {login_url}"
    )
    return subject, headline, body_html, text


def build_email_verification_email(context):
    verify_url = escape(context.get("verify_url", ""))
    creator_first_name = escape(str(context.get("creator_first_name", "") or ""))
    creator_last_name = escape(str(context.get("creator_last_name", "") or ""))
    creator_email = escape(str(context.get("creator_email", "") or ""))
    username = escape(str(context.get("username", "") or ""))
    password = escape(str(context.get("password", "") or ""))

    creator_identity = ""
    if creator_first_name or creator_last_name or creator_email:
        full_name = " ".join(part for part in [creator_first_name, creator_last_name] if part).strip()
        if full_name and creator_email:
            creator_identity = f"{full_name} ({creator_email})"
        else:
            creator_identity = full_name or creator_email

    admin_context_html = ""
    if creator_identity or username or password:
        admin_context_html = (
            "<p>Ο λογαριασμός διαχειριστή σας δημιουργήθηκε από τον διαχειριστή "
            f"<strong>{creator_identity}</strong>."
            " Παρακάτω θα βρείτε το όνομα χρήστη και τον κωδικό πρόσβασης με τα οποία μπορείτε να "
            "συνδεθείτε και να διαχειριστείτε αιτήσεις, θέσεις, επιστημονικά πεδία κ.α.</p>"
            "<p><strong>Στοιχεία σύνδεσης:</strong></p>"
            "<ul style=\"margin:0 0 16px 18px;padding:0;\">"
            "<li>Το email αυτό</li>"
            f"<li>Κωδικός πρόσβασης: <strong>{password}</strong>.</li>"
            "</ul>"
        )

    subject = "Επιβεβαίωση email στο ProfRanker"
    headline = "Ολοκληρώστε την επιβεβαίωση της ηλεκτρονικής σας διεύθυνσης."
    body_html = (
        f"{admin_context_html}"
        "<p>Για να ενεργοποιηθεί ο λογαριασμός σας και να αποκτήσετε πρόσβαση στις λειτουργίες του ProfRanker, "
        "παρακαλώ επιβεβαιώστε το email σας.</p>"
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{verify_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Επιβεβαίωση email"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    admin_context_text = ""
    if creator_identity or username or password:
        admin_context_text = (
            f"Δημιουργία λογαριασμού από: {creator_identity}. "
            f"Στοιχεία σύνδεσης: - Το email αυτό - Κωδικός πρόσβασης: {password}. "
        )
    text = (
        f"{admin_context_text}"
        "Για να ενεργοποιηθεί ο λογαριασμός σας και να αποκτήσετε πρόσβαση στις λειτουργίες του ProfRanker, "
        "παρακαλώ επιβεβαιώστε το email σας. "
        f"Επιβεβαίωση: {verify_url}"
    )
    return subject, headline, body_html, text


def build_application_submission_email(context):
    scientific_field = escape(context.get("scientific_field", ""))
    end_date = escape(context.get("end_date", ""))
    application_id = context.get("application_id")
    cta_url = context.get("application_url") or _frontend_url(f"/application-score/{application_id}")

    subject = f"Επιβεβαίωση υποβολής αίτησης ({scientific_field})"
    headline = (
        "Η αίτησή σας για το επιστημονικό πεδίο "
        f"<strong>{scientific_field}</strong> υποβλήθηκε επιτυχώς!"
    )
    body_html = (
        "<p>Η αίτησή σας καταχωρήθηκε στο ProfRanker και είναι πλέον σε κατάσταση "
        "υποβολής. Μπορείτε να δείτε τα στοιχεία της αίτησης καθώς και την βαθμολογία "
        "της ή να την επεξεργαστείτε/διαγράψετε μέχρι τις "
        f"<strong>{end_date}</strong>.</p>"
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{cta_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Προβολή αίτησης"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    text = (
        "Η αίτησή σας για το επιστημονικό πεδίο "
        f"{scientific_field} υποβλήθηκε επιτυχώς. "
        "Η αίτησή σας καταχωρήθηκε στο ProfRanker και είναι πλέον σε κατάσταση υποβολής. "
        "Μπορείτε να δείτε τα στοιχεία της αίτησης καθώς και την βαθμολογία της ή να την "
        f"επεξεργαστείτε/διαγράψετε μέχρι τις {end_date}. "
        f"Προβολή αίτησης: {cta_url}"
    )
    return subject, headline, body_html, text


def build_application_resubmission_email(context):
    scientific_field = escape(context.get("scientific_field", ""))
    end_date = escape(context.get("end_date", ""))
    application_id = context.get("application_id")
    cta_url = context.get("application_url") or _frontend_url(f"/application-score/{application_id}")

    subject = f"Επιβεβαίωση επανυποβολής αίτησης ({scientific_field})"
    headline = (
        "Οι αλλαγές σας για το επιστημονικό πεδίο "
        f"<strong>{scientific_field}</strong> καταχωρήθηκαν!"
    )
    body_html = (
        "<p>Η αίτησή σας ενημερώθηκε και επανυποβλήθηκε επιτυχώς.</p>"
        "<p>Μπορείτε να δείτε τα στοιχεία της αίτησης καθώς και την βαθμολογία της ή "
        "να την επεξεργαστείτε/διαγράψετε μέχρι τις "
        f"<strong>{end_date}</strong>.</p>"
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{cta_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Προβολή αίτησης"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    text = (
        "Οι αλλαγές σας για το επιστημονικό πεδίο "
        f"{scientific_field} καταχωρήθηκαν. "
        "Η αίτησή σας ενημερώθηκε και επανυποβλήθηκε επιτυχώς. "
        "Μπορείτε να δείτε τα στοιχεία της αίτησης καθώς και την βαθμολογία της ή να την "
        f"επεξεργαστείτε/διαγράψετε μέχρι τις {end_date}. "
        f"Προβολή αίτησης: {cta_url}"
    )
    return subject, headline, body_html, text


def build_position_closed_email(context):
    scientific_field = escape(context.get("scientific_field", ""))
    cta_url = context.get("ranking_url") or _frontend_url("/ranking")

    subject = f"Λήξη περιόδου αιτήσεων για ({scientific_field})"
    headline = "Οι αιτήσεις μόλις έκλεισαν!"
    body_html = (
        "<p>Η διαδικασία υποβολής αιτήσεων και τελικής αξιολόγησής τους για το "
        f"επιστημονικό πεδίο <strong>{scientific_field}</strong> είναι πλέον ολοκληρωμένη. "
        "Συνδεθείτε για να δείτε τη θέση σας στη λίστα κατάταξης των υποψηφίων.</p>"
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{cta_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Προβολή κατάταξης"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    text = (
        "Η διαδικασία υποβολής αιτήσεων και τελικής αξιολόγησής τους για το "
        f"επιστημονικό πεδίο {scientific_field} είναι πλέον ολοκληρωμένη. "
        "Συνδεθείτε για να δείτε τη θέση σας στη λίστα κατάταξης των υποψηφίων. "
        f"Προβολή κατάταξης: {cta_url}"
    )
    return subject, headline, body_html, text


EMAIL_TEMPLATE_BUILDERS = {
    "guest_registration": build_guest_registration_email,
    "admin_registration": build_admin_registration_email,
    "email_verification": build_email_verification_email,
    "application_submitted": build_application_submission_email,
    "application_resubmitted": build_application_resubmission_email,
    "position_closed": build_position_closed_email,
}


def build_email_payload(template_key, context=None):
    context = context or {}
    builder = EMAIL_TEMPLATE_BUILDERS.get(template_key)
    if not builder:
        raise KeyError(f"Unknown email template: {template_key}")
    return builder(context)
