import re
import logging
from pypdf import PdfReader
from app.models import PhdCheck, PhdDocument

MIN_PHD_PDF_PAGES = 10
MIN_PHD_TEXT_CHARS = 10000

logger = logging.getLogger(__name__)


def _normalize_whitespace(text):
    return " ".join(text.split())


def _strip_nul_chars(text):
    return text.replace("\x00", "")


def _count_non_whitespace(text):
    return len(re.sub(r"\s+", "", text))


def _extract_phd_pdf(file_handle, log_id=None):
    try:
        reader = PdfReader(file_handle)
        page_count = len(reader.pages)
        if page_count == 0:
            logger.warning("PhD PDF processing failed: empty PDF (id=%s)", log_id)
            raise ValueError("empty")
        if page_count < MIN_PHD_PDF_PAGES:
            logger.warning(
                "PhD PDF processing failed: page count %s < %s (id=%s)",
                page_count,
                MIN_PHD_PDF_PAGES,
                log_id,
            )
            return {
                "status": "failed",
                "error": "Το PDF πρέπει να έχει τουλάχιστον 10 σελίδες.",
                "page_count": page_count,
                "text": "",
                "text_length": 0,
            }

        raw_text_parts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                raw_text_parts.append(page_text)

        raw_text = "\n".join(raw_text_parts)
        normalized = _normalize_whitespace(_strip_nul_chars(raw_text))
        text_length = _count_non_whitespace(normalized)

        logger.info(
            "PhD PDF processing stats (id=%s): pages=%s, extracted_chars=%s",
            log_id,
            page_count,
            text_length,
        )

        if text_length == 0:
            logger.warning("PhD PDF processing failed: no extractable text (id=%s)", log_id)
            return {
                "status": "failed",
                "error": (
                    "Το ανεβασμένο PDF διδακτορικής διατριβής δεν περιέχει αρκετό εξαγώγιμο κείμενο. "
                    "Παρακαλώ ανεβάστε PDF με αναγνώσιμο κείμενο."
                ),
                "page_count": page_count,
                "text": normalized,
                "text_length": text_length,
            }

        if text_length < MIN_PHD_TEXT_CHARS:
            logger.warning(
                "PhD PDF processing failed: extracted text %s < %s (id=%s)",
                text_length,
                MIN_PHD_TEXT_CHARS,
                log_id,
            )
            return {
                "status": "failed",
                "error": "Το εξαγώγιμο κείμενο είναι ανεπαρκές (τουλάχιστον 10.000 χαρακτήρες χωρίς κενά).",
                "page_count": page_count,
                "text": normalized,
                "text_length": text_length,
            }

        return {
            "status": "success",
            "error": None,
            "page_count": page_count,
            "text": normalized,
            "text_length": text_length,
        }
    except ValueError:
        logger.exception("PhD PDF processing failed with ValueError (id=%s)", log_id)
        return {
            "status": "failed",
            "error": "Το PDF είναι κενό ή δεν μπορεί να αναγνωστεί.",
            "page_count": None,
            "text": "",
            "text_length": 0,
        }
    except Exception:
        logger.exception("PhD PDF processing failed with Exception (id=%s)", log_id)
        return {
            "status": "failed",
            "error": "Το PDF δεν μπορεί να διαβαστεί ή είναι κατεστραμμένο.",
            "page_count": None,
            "text": "",
            "text_length": 0,
        }


def process_phd_pdf(document_id):
    doc = PhdDocument.objects.select_related("application").filter(id=document_id).first()
    if not doc:
        logger.warning("PhD PDF processing failed: document not found (id=%s)", document_id)
        return False, "Το έγγραφο διδακτορικής διατριβής δεν βρέθηκε."

    doc.extraction_status = "pending"
    doc.extraction_error = None
    doc.extracted_raw_text = None
    doc.page_count = None
    doc.extracted_text_length = 0
    doc.save(update_fields=[
        "extraction_status",
        "extraction_error",
        "extracted_raw_text",
        "page_count",
        "extracted_text_length",
        "updated_at",
    ])

    if not doc.pdf_file:
        logger.warning("PhD PDF processing failed: missing file (id=%s)", document_id)
        doc.extraction_status = "failed"
        doc.extraction_error = "Λείπει το αρχείο PDF της διδακτορικής διατριβής."
        doc.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False, doc.extraction_error

    with doc.pdf_file.open("rb") as fh:
        result = _extract_phd_pdf(fh, log_id=document_id)

    doc.extraction_status = result["status"]
    doc.extraction_error = result["error"]
    doc.page_count = result["page_count"]
    doc.extracted_raw_text = result["text"] if result["status"] == "success" else None
    doc.extracted_text_length = result["text_length"]
    doc.save(update_fields=[
        "extraction_status",
        "extraction_error",
        "page_count",
        "extracted_raw_text",
        "extracted_text_length",
        "updated_at",
    ])

    if result["status"] == "success":
        logger.info("PhD PDF processing succeeded (id=%s)", document_id)
        return True, None

    return False, result["error"]


def process_phd_check(check_id):
    check = PhdCheck.objects.select_related("vault_document").filter(id=check_id).first()
    if not check:
        logger.warning("PhD check failed: check not found (id=%s)", check_id)
        return False, "Το αρχείο ελέγχου δεν βρέθηκε."

    check.extraction_status = "pending"
    check.extraction_error = None
    check.extracted_raw_text = None
    check.page_count = None
    check.extracted_text_length = 0
    check.save(update_fields=[
        "extraction_status",
        "extraction_error",
        "extracted_raw_text",
        "page_count",
        "extracted_text_length",
        "updated_at",
    ])

    vault_file = check.vault_document.file if check.vault_document else None
    if not vault_file:
        check.extraction_status = "failed"
        check.extraction_error = "Λείπει το αρχείο PDF της διδακτορικής διατριβής."
        check.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False, check.extraction_error

    with vault_file.open("rb") as fh:
        result = _extract_phd_pdf(fh, log_id=check_id)

    check.extraction_status = result["status"]
    check.extraction_error = result["error"]
    check.page_count = result["page_count"]
    check.extracted_raw_text = result["text"] if result["status"] == "success" else None
    check.extracted_text_length = result["text_length"]
    check.save(update_fields=[
        "extraction_status",
        "extraction_error",
        "page_count",
        "extracted_raw_text",
        "extracted_text_length",
        "updated_at",
    ])

    if result["status"] == "success":
        logger.info("PhD check succeeded (id=%s)", check_id)
        return True, None

    return False, result["error"]
