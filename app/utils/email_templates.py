from html import escape


def build_guest_registration_email(context=None):
    cta_html = (
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        "<a href=\"https://profrankerapp.com/login\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Σύνδεση"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    subject = "Επιβεβαίωση εγγραφής στο ProfRanker"
    headline = (
        "Καλώς ήρθατε στο ProfRanker, το σύστημα αυτόματης αξιολόγησης "
        "υποψηφίων καθηγητών του Πανεπιστημίου Πατρών!"
    )
    body_html = (
        "<p>Η εγγραφή σας ολοκληρώθηκε με επιτυχία. Μπορείτε πλέον να συνδεθείτε "
        "και να υποβάλετε αίτηση στις διαθέσιμες θέσεις.</p>"
        f"{cta_html}"
    )
    text = (
        "Η εγγραφή σας ολοκληρώθηκε με επιτυχία. Μπορείτε πλέον να συνδεθείτε "
        "και να υποβάλετε αίτηση στις διαθέσιμες θέσεις."
    )
    return subject, headline, body_html, text


def build_admin_registration_email(context=None):
    cta_html = (
        "<table role=\"presentation\" align=\"center\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"margin:18px auto 8px;\">"
        "<tr>"
        "<td align=\"center\">"
        "<a href=\"https://profrankerapp.com/login\" "
        "style=\"display:inline-block;background:#633439;color:#ffffff;text-decoration:none;"
        "padding:10px 18px;border-radius:8px;font-weight:600;\">"
        "Σύνδεση διαχειριστή"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
    )
    subject = "Επιβεβαίωση εγγραφής ως διαχειριστής στο ProfRanker"
    headline = (
        "Καλώς ήρθατε ως διαχειριστής στο ProfRanker, το σύστημα αυτόματης "
        "αξιολόγησης υποψηφίων καθηγητών του Πανεπιστημίου Πατρών!"
    )
    body_html = (
        "<p>Ο λογαριασμός διαχειριστή σας δημιουργήθηκε. Μπορείτε να συνδεθείτε "
        "και να διαχειριστείτε αιτήσεις, θέσεις, επιστημονικά πεδία κ.α.</p>"
        f"{cta_html}"
    )
    text = (
        "Ο λογαριασμός διαχειριστή σας δημιουργήθηκε. Μπορείτε να συνδεθείτε "
        "και να διαχειριστείτε αιτήσεις, θέσεις, επιστημονικά πεδία κ.α."
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
