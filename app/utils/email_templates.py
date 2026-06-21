from html import escape


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
    login_url = escape(context.get("login_url") or "https://profrankerapp.com/login")
    cta_html = (
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        f"<a href=\"{login_url}\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Αλλαγή κωδικού και σύνδεση"
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
        "<p>Ο λογαριασμός διαχειριστή σας δημιουργήθηκε. Μπορείτε να συνδεθείτε "
        "και να διαχειριστείτε αιτήσεις, θέσεις, επιστημονικά πεδία κ.α.</p>"
        "<p><strong>Σημαντικό:</strong> Επειδή ο αρχικός κωδικός ορίστηκε από άλλον διαχειριστή, "
        "στην πρώτη σύνδεση θα σας ζητηθεί υποχρεωτικά να τον αλλάξετε πριν συνεχίσετε.</p>"
        f"{cta_html}"
    )
    text = (
        "Ο λογαριασμός διαχειριστή σας δημιουργήθηκε. Μπορείτε να συνδεθείτε "
        "και να διαχειριστείτε αιτήσεις, θέσεις, επιστημονικά πεδία κ.α. "
        "Σημαντικό: Στην πρώτη σύνδεση θα σας ζητηθεί υποχρεωτικά αλλαγή κωδικού. "
        f"Σύνδεση: {login_url}"
    )
    return subject, headline, body_html, text


def build_email_verification_email(context):
    verify_url = escape(context.get("verify_url", ""))

    subject = "Επιβεβαίωση email στο ProfRanker"
    headline = "Ολοκληρώστε την επιβεβαίωση της ηλεκτρονικής σας διεύθυνσης."
    body_html = (
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
    text = (
        "Για να ενεργοποιηθεί ο λογαριασμός σας και να αποκτήσετε πρόσβαση στις λειτουργίες του ProfRanker, "
        "παρακαλώ επιβεβαιώστε το email σας. "
        f"Επιβεβαίωση: {verify_url}"
    )
    return subject, headline, body_html, text


def build_application_submission_email(context):
    scientific_field = escape(context.get("scientific_field", ""))
    end_date = escape(context.get("end_date", ""))
    application_id = context.get("application_id")
    cta_url = f"https://profrankerapp.com/application-score/{application_id}"

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
    cta_url = f"https://profrankerapp.com/application-score/{application_id}"

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
    cta_url = "https://profrankerapp.com/ranking"

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
