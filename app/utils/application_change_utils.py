import os
from datetime import date, datetime
from html import escape

from app.models import ApplicationDocument, Publication, VaultDocument


def _normalize_string(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_bool(value):
    if value is None:
        return False
    return bool(value)


def _format_bool(value):
    return "Ναι" if value else "Όχι"


def _format_value(value):
    if value in {None, ""}:
        return "—"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            parts = text.split("-")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return text
    return str(value)


def _format_publication_value(value):
    if value in {None, ""}:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            parts = text.split("-")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return text
    return str(value)


def _format_diff_html(old_value, new_value):
    old_html = escape(_format_value(old_value))
    new_html = escape(_format_value(new_value))
    return (
        f"<span style=\"color:#b91c1c;font-weight:600;\">{old_html}</span>"
        " → "
        f"<span style=\"color:#166534;font-weight:600;\">{new_html}</span>"
    )


def _format_publication_diff_html(old_value, new_value):
    old_html = escape(_format_publication_value(old_value))
    new_html = escape(_format_publication_value(new_value))
    return (
        f"<span style=\"color:#b91c1c;font-weight:600;\">{old_html}</span>"
        " → "
        f"<span style=\"color:#166534;font-weight:600;\">{new_html}</span>"
    )


def _publication_display(values):
    return " | ".join([part for part in values if part])


def _publication_field_values(publication):
    authors = publication.authors or []
    if isinstance(authors, list):
        authors_text = ", ".join([_normalize_string(a) for a in authors if _normalize_string(a)])
    else:
        authors_text = _normalize_string(authors)

    return {
        "type": _normalize_string(publication.type),
        "publication_title": _normalize_string(publication.publication_title),
        "journal_conf_title": _normalize_string(publication.journal_conf_title),
        "year": _normalize_string(publication.year),
        "issn": _normalize_string(publication.issn),
        "authors": authors_text,
        "publisher": _normalize_string(publication.publisher),
    }


def _publication_fields_for_type(pub_type):
    if pub_type == "journal":
        return ["publication_title", "journal_conf_title", "year", "issn", "authors"]
    if pub_type == "conference_proceedings":
        return ["publication_title", "journal_conf_title", "year", "publisher", "authors"]
    if pub_type == "conference_presentation":
        return ["publication_title", "journal_conf_title", "year", "authors"]
    if pub_type in {"book", "monograph"}:
        return ["publication_title", "year", "publisher", "authors"]
    return ["publication_title", "year", "authors"]


def build_application_snapshot(application):
    document_types = [doc_type for doc_type, _ in VaultDocument.DOCUMENT_TYPES]
    documents = {doc_type: [] for doc_type in document_types}
    links = (
        ApplicationDocument.objects.filter(application=application)
        .select_related("vault_document")
        .order_by("created_at", "id")
    )

    for link in links:
        filename = None
        if link.vault_document and link.vault_document.file:
            filename = os.path.basename(link.vault_document.file.name)
        if not filename:
            filename = f"#{link.vault_document_id}"
        documents.setdefault(link.doc_type, []).append(filename)

    for doc_type in documents:
        documents[doc_type] = sorted(documents[doc_type])

    publications = Publication.objects.filter(application=application).order_by("id")
    publication_entries = []
    for pub in publications:
        publication_entries.append(
            {
                "id": pub.id,
                **_publication_field_values(pub),
            }
        )

    return {
        "phone_number": _normalize_string(application.phone_number),
        "landline_number": _normalize_string(application.landline_number),
        "street_address": _normalize_string(application.street_address),
        "city": _normalize_string(application.city),
        "postal_code": _normalize_string(application.postal_code),
        "is_public_employee": _normalize_bool(application.is_public_employee),
        "phd_title": _normalize_string(application.phd_title),
        "phd_acquisition_date": _normalize_string(application.phd_acquisition_date),
        "phd_is_from_foreign_institute": _normalize_bool(
            application.phd_is_from_foreign_institute
        ),
        "work_experience": _normalize_string(application.work_experience),
        "has_not_participated_in_past_program": _normalize_bool(
            application.has_not_participated_in_past_program
        ),
        "is_eu_citizen_non_greek": _normalize_bool(application.is_eu_citizen_non_greek),
        "documents": documents,
        "publications": publication_entries,
    }


def diff_application_snapshots(previous, current):
    if previous == current:
        return False, "", ""

    labels = {
        "phone_number": "Κινητό",
        "landline_number": "Σταθερό",
        "street_address": "Διεύθυνση",
        "city": "Πόλη",
        "postal_code": "ΤΚ",
        "is_public_employee": "Δημόσιος υπάλληλος",
        "phd_title": "Τίτλος διδακτορικού",
        "phd_acquisition_date": "Ημ/νία λήψης διδακτορικού",
        "phd_is_from_foreign_institute": "Τίτλος από ξένο ίδρυμα",
        "work_experience": "Εργασιακή εμπειρία (έτη)",
        "has_not_participated_in_past_program": "Μη παλαιότερη συμμετοχή στο πρόγραμμα",
        "is_eu_citizen_non_greek": "Πολίτης ΕΕ (εκτός Ελλάδας)",
    }

    doc_labels = {
        "cv": "Βιογραφικό",
        "phd": "Διδακτορικό",
        "doatap": "ΔΟΑΤΑΠ",
        "course_plan": "Σχεδιάγραμμα διδασκαλίας",
        "military": "Στρατολογική κατάσταση",
        "public_employee_permission": "Άδεια δημόσιου υπαλλήλου",
        "not_participated_declaration": "Υπεύθυνη δήλωση μη συμμετοχής σε προηγούμενο πρόγραμμα",
        "eu_citizen_greek_language_certificate": "Πιστοποιητικό ελληνομάθειας",
        "responsible_declaration": "Υπεύθυνη δήλωση αποδοχής όρων",
        "bio_supporting": "Συμπληρωματικά βιογραφικού",
        "employment_certificate": "Βεβαιώσεις εργασίας",
        "other": "Λοιπά δικαιολογητικά",
    }

    changes = []
    changes_text = []

    for field, label in labels.items():
        old = previous.get(field)
        new = current.get(field)
        if old == new:
            continue
        if field in {"is_public_employee", "phd_is_from_foreign_institute", "has_not_participated_in_past_program", "is_eu_citizen_non_greek"}:
            old_value = _format_bool(old)
            new_value = _format_bool(new)
        else:
            old_value = _format_value(old)
            new_value = _format_value(new)
        line = f"{label}: {_format_diff_html(old_value, new_value)}"
        changes.append(line)
        changes_text.append(f"{label}: {old_value} → {new_value}")

    old_docs = previous.get("documents", {})
    new_docs = current.get("documents", {})
    for doc_type, label in doc_labels.items():
        old_list = old_docs.get(doc_type, [])
        new_list = new_docs.get(doc_type, [])
        if old_list == new_list:
            continue
        removed = [item for item in old_list if item not in new_list]
        added = [item for item in new_list if item not in old_list]
        for item in added:
            colored = (
                f"{label}: <span style=\"color:#166534;font-weight:600;\">{escape(item)}</span> "
                "<span style=\"color:#166534;font-weight:600;\">(Προστέθηκε)</span>"
            )
            changes.append(colored)
            changes_text.append(f"{label}: {item} (Προστέθηκε)")
        for item in removed:
            colored = (
                f"{label}: <span style=\"color:#b91c1c;font-weight:600;\">{escape(item)}</span> "
                "<span style=\"color:#b91c1c;font-weight:600;\">(Αφαιρέθηκε)</span>"
            )
            changes.append(colored)
            changes_text.append(f"{label}: {item} (Αφαιρέθηκε)")

    old_pubs = {item["id"]: item for item in previous.get("publications", [])}
    new_pubs = {item["id"]: item for item in current.get("publications", [])}

    added_pub_ids = [pub_id for pub_id in new_pubs if pub_id not in old_pubs]
    removed_pub_ids = [pub_id for pub_id in old_pubs if pub_id not in new_pubs]
    changed_pub_ids = []

    for pub_id in new_pubs:
        if pub_id in old_pubs and new_pubs[pub_id] != old_pubs[pub_id]:
            changed_pub_ids.append(pub_id)

    if added_pub_ids or removed_pub_ids or changed_pub_ids:
        changes.append("<strong>Δημοσιεύσεις:</strong>")
        changes_text.append("Δημοσιεύσεις:")

    if added_pub_ids:
        title = "Προστέθηκε" if len(added_pub_ids) == 1 else "Προστέθηκαν"
        changes.append(f"<div style=\"margin-top:6px;\"><strong>{title}:</strong></div>")
        changes_text.append(f"{title}:")
        for pub_id in added_pub_ids:
            pub = new_pubs[pub_id]
            field_keys = _publication_fields_for_type(pub.get("type"))
            display = _publication_display(
                [escape(_format_publication_value(pub.get(key, ""))) for key in field_keys]
            )
            if display:
                changes.append(f"<div>{display}</div>")
                changes_text.append(display)

    if removed_pub_ids:
        title = "Αφαιρέθηκε" if len(removed_pub_ids) == 1 else "Αφαιρέθηκαν"
        changes.append(f"<div style=\"margin-top:6px;\"><strong>{title}:</strong></div>")
        changes_text.append(f"{title}:")
        for pub_id in removed_pub_ids:
            pub = old_pubs[pub_id]
            field_keys = _publication_fields_for_type(pub.get("type"))
            display = _publication_display(
                [escape(_format_publication_value(pub.get(key, ""))) for key in field_keys]
            )
            if display:
                changes.append(f"<div>{display}</div>")
                changes_text.append(display)

    if changed_pub_ids:
        title = "Άλλαξε" if len(changed_pub_ids) == 1 else "Άλλαξαν"
        changes.append(f"<div style=\"margin-top:6px;\"><strong>{title}:</strong></div>")
        changes_text.append(f"{title}:")
        for pub_id in changed_pub_ids:
            old_pub = old_pubs[pub_id]
            new_pub = new_pubs[pub_id]
            field_keys = _publication_fields_for_type(old_pub.get("type"))
            for key in _publication_fields_for_type(new_pub.get("type")):
                if key not in field_keys:
                    field_keys.append(key)

            display_parts = []
            text_parts = []
            for key in field_keys:
                old_value = old_pub.get(key, "")
                new_value = new_pub.get(key, "")
                if not old_value and not new_value:
                    continue
                if old_value == new_value:
                    value = escape(_format_publication_value(new_value))
                    if value:
                        display_parts.append(value)
                        text_parts.append(_format_publication_value(new_value))
                    continue
                display_parts.append(_format_publication_diff_html(old_value, new_value))
                text_parts.append(
                    f"{_format_publication_value(old_value)} → {_format_publication_value(new_value)}"
                )

            display_line = _publication_display(display_parts)
            text_line = " | ".join([part for part in text_parts if part])
            if display_line:
                changes.append(f"<div>{display_line}</div>")
                changes_text.append(text_line)

    if not changes:
        return False, "", ""

    html_list = "<div>" + "".join(
        f"<div>{line}</div>" for line in changes
    ) + "</div>"
    text_list = "\n".join(changes_text)

    return True, html_list, text_list
