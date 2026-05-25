import re
import logging
from pypdf import PdfReader
from app.models import PhdDocument

MIN_PHD_PDF_PAGES = 10
MIN_PHD_TEXT_CHARS = 10000

logger = logging.getLogger(__name__)


def _normalize_whitespace(text):
    return " ".join(text.split())


def _strip_nul_chars(text):
    return text.replace("\x00", "")


def _count_non_whitespace(text):
    return len(re.sub(r"\s+", "", text))


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

    try:
        with doc.pdf_file.open("rb") as fh:
            reader = PdfReader(fh)
            page_count = len(reader.pages)
            if page_count == 0:
                logger.warning("PhD PDF processing failed: empty PDF (id=%s)", document_id)
                raise ValueError("empty")
            if page_count < MIN_PHD_PDF_PAGES:
                logger.warning(
                    "PhD PDF processing failed: page count %s < %s (id=%s)",
                    page_count,
                    MIN_PHD_PDF_PAGES,
                    document_id,
                )
                doc.extraction_status = "failed"
                doc.extraction_error = "Το PDF πρέπει να έχει τουλάχιστον 10 σελίδες."
                doc.page_count = page_count
                doc.save(update_fields=["extraction_status", "extraction_error", "page_count", "updated_at"])
                return False, doc.extraction_error

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
                document_id,
                page_count,
                text_length,
            )

            doc.page_count = page_count
            doc.extracted_raw_text = normalized
            doc.extracted_text_length = text_length

            if text_length == 0:
                logger.warning("PhD PDF processing failed: no extractable text (id=%s)", document_id)
                doc.extraction_status = "failed"
                doc.extraction_error = (
                    "Το ανεβασμένο PDF διδακτορικής διατριβής δεν περιέχει αρκετό εξαγώγιμο κείμενο. "
                    "Παρακαλώ ανεβάστε PDF με αναγνώσιμο κείμενο."
                )
                doc.save(update_fields=[
                    "extraction_status",
                    "extraction_error",
                    "page_count",
                    "extracted_raw_text",
                    "extracted_text_length",
                    "updated_at",
                ])
                return False, doc.extraction_error

            if text_length < MIN_PHD_TEXT_CHARS:
                logger.warning(
                    "PhD PDF processing failed: extracted text %s < %s (id=%s)",
                    text_length,
                    MIN_PHD_TEXT_CHARS,
                    document_id,
                )
                doc.extraction_status = "failed"
                doc.extraction_error = "Το εξαγώγιμο κείμενο είναι ανεπαρκές (τουλάχιστον 10.000 χαρακτήρες χωρίς κενά)."
                doc.save(update_fields=[
                    "extraction_status",
                    "extraction_error",
                    "page_count",
                    "extracted_raw_text",
                    "extracted_text_length",
                    "updated_at",
                ])
                return False, doc.extraction_error

            doc.extraction_status = "success"
            doc.extraction_error = None
            doc.save(update_fields=[
                "extraction_status",
                "extraction_error",
                "page_count",
                "extracted_raw_text",
                "extracted_text_length",
                "updated_at",
            ])
            logger.info("PhD PDF processing succeeded (id=%s)", document_id)
            return True, None

    except ValueError:
        doc.extraction_status = "failed"
        doc.extraction_error = "Το PDF είναι κενό ή δεν μπορεί να αναγνωστεί."
        doc.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        logger.exception("PhD PDF processing failed with ValueError (id=%s)", document_id)
        return False, doc.extraction_error
    except Exception:
        doc.extraction_status = "failed"
        doc.extraction_error = "Το PDF δεν μπορεί να διαβαστεί ή είναι κατεστραμμένο."
        doc.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        logger.exception("PhD PDF processing failed with Exception (id=%s)", document_id)
        return False, doc.extraction_error
