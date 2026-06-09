import json
import logging
import os

from openai import OpenAI

from app.models import (
    Application,
    CoursePlan,
    CoursePlanEmbedding,
    CoursePlanProfile,
    Course,
    PhdEmbedding,
    PhdProfile,
    ScientificField,
    ScientificFieldEmbedding,
    ScientificFieldProfile,
)
from app.services.submission_progress import set_submission_progress_safe

logger = logging.getLogger(__name__)


def normalize_source_text(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("OPENAI_API_KEY is missing; skipping translation/keyword extraction.")
        return None
    return OpenAI(api_key=api_key)


def translate_source_text(source_text, model):
    client = get_openai_client()
    if not client:
        return ""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Translate Greek academic text to English. Preserve meaning, keep academic tone, and keep proper nouns. Return only the translated text.",
                },
                {"role": "user", "content": source_text},
            ],
            temperature=0,
        )
    except Exception as exc:
        logger.exception("Translation request failed: %s", exc)
        return ""
    translated = (response.choices[0].message.content or "").strip()
    if not translated:
        logger.warning("Translation returned empty content.")
    return translated


def detect_language(source_text, model=None):
    if not source_text:
        return "gr"

    letters = [char for char in source_text if char.isalpha()]
    if not letters:
        return "gr"

    greek_count = sum(
        1
        for char in letters
        if ("\u0370" <= char <= "\u03FF") or ("\u1F00" <= char <= "\u1FFF")
    )
    latin_count = sum(
        1
        for char in letters
        if ("A" <= char <= "Z") or ("a" <= char <= "z")
    )

    if greek_count == 0 and latin_count == 0:
        return "gr"

    return "gr" if greek_count >= latin_count else "en"


def translate_text(source_text, target_language, model):
    client = get_openai_client()
    if not client or not source_text:
        return ""
    target_label = "Greek" if target_language == "gr" else "English"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate academic text to {target_label}. Preserve meaning, keep academic tone, and keep proper nouns. "
                        "Return only the translated text."
                    ),
                },
                {"role": "user", "content": source_text},
            ],
            temperature=0,
        )
    except Exception as exc:
        logger.exception("Translation request failed: %s", exc)
        return ""
    translated = (response.choices[0].message.content or "").strip()
    if not translated:
        logger.warning("Translation returned empty content.")
    return translated


def translate_keywords(keywords, target_language, model):
    client = get_openai_client()
    if not client or not keywords:
        return []
    target_label = "Greek" if target_language == "gr" else "English"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate keyword list to {target_label}. Preserve academic terms. "
                        "Return JSON with key keywords as a list of strings."
                    ),
                },
                {"role": "user", "content": json.dumps({"keywords": keywords})},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.exception("Keyword translation failed: %s", exc)
        return []
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Keyword translation returned invalid JSON: %s", content)
        return []
    translated = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
    return translated


def extract_keywords_bilingual(source_text, model):
    client = get_openai_client()
    if not client:
        return [], []
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You extract academic keywords from Greek text.",
                },
                {
                    "role": "user",
                    "content": (
                        "Εξήγαγε 8–15 ακαδημαϊκές λέξεις-κλειδιά που περιγράφουν το επιστημονικό πεδίο. "
                        "Μην εισάγεις έννοιες που δεν υπάρχουν ή δεν τεκμηριώνονται από το κείμενο. "
                        "Δώσε τις λέξεις στα ελληνικά και, όπου είναι χρήσιμο, αγγλικό ισοδύναμο. "
                        "Επέστρεψε μόνο JSON με τα κλειδιά keywords_gr και keywords_en (λίστες).\n\n"
                        f"Κείμενο:\n{source_text}"
                    ),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.exception("Keyword extraction request failed: %s", exc)
        return [], []
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Keyword extraction returned invalid JSON: %s", content)
        return [], []
    keywords_gr = [str(k).strip() for k in data.get("keywords_gr", []) if str(k).strip()]
    keywords_en = [str(k).strip() for k in data.get("keywords_en", []) if str(k).strip()]
    if not keywords_gr and not keywords_en:
        logger.warning("Keyword extraction returned empty lists.")
    return keywords_gr, keywords_en


def generate_embedding(text, model):
    client = get_openai_client()
    if not client or not text:
        return None
    try:
        response = client.embeddings.create(model=model, input=text)
    except Exception as exc:
        logger.exception("Embedding request failed: %s", exc)
        return None
    if not response.data:
        logger.warning("Embedding response had no data.")
        return None
    return response.data[0].embedding


def upsert_scientific_field_embeddings(scientific_field, profile_text, profile_text_en, model):
    ScientificFieldEmbedding.objects.filter(scientific_field=scientific_field).delete()
    embedding_gr = generate_embedding(profile_text, model)
    if embedding_gr:
        ScientificFieldEmbedding.objects.create(
            scientific_field=scientific_field,
            model_name=model,
            language="gr",
            vector=embedding_gr,
        )

    embedding_en = generate_embedding(profile_text_en, model)
    if embedding_en:
        ScientificFieldEmbedding.objects.create(
            scientific_field=scientific_field,
            model_name=model,
            language="en",
            vector=embedding_en,
        )


def build_phd_profile_text(title, abstract, keywords, language):
    if language == "en":
        title_label = "Thesis Title"
        abstract_label = "Abstract"
        keywords_label = "Keywords"
    else:
        title_label = "Τίτλος διατριβής"
        abstract_label = "Περίληψη"
        keywords_label = "Λέξεις-κλειδιά"
    text = f"{title_label}: {normalize_source_text(title)}".strip()
    if abstract:
        text = f"{text}\n\n{abstract_label}:\n{normalize_source_text(abstract)}"
    if keywords:
        text = f"{text}\n\n{keywords_label}:\n{', '.join([normalize_source_text(k) for k in keywords])}"
    return text.strip()


def upsert_phd_embeddings(phd_degree, profile_text, language, model):
    PhdEmbedding.objects.filter(phd_degree=phd_degree).delete()
    embedding_vector = generate_embedding(profile_text, model)
    if embedding_vector:
        PhdEmbedding.objects.create(
            phd_degree=phd_degree,
            model_name=model,
            language=language,
            vector=embedding_vector,
        )
        return True
    return False


def build_course_plan_profile_text(course_plans, language):
    if language == "en":
        course_label = "Course"
        labels = {
            "general_description": "General course description",
            "learning_objectives": "Learning objectives",
            "course_schedule": "Course schedule - Teaching material",
            "delivery_methods": "Delivery mode & teaching methods",
            "bibliography_material": "Bibliography - Educational material",
            "learning_outcomes": "Learning outcomes",
            "assessment_methods_criteria": "Assessment methods and criteria",
        }
    else:
        course_label = "Μάθημα"
        labels = {
            "general_description": "Γενική περιγραφή μαθήματος",
            "learning_objectives": "Μαθησιακοί στόχοι",
            "course_schedule": "Προγραμματισμός μαθημάτων - Διδακτέα ύλη",
            "delivery_methods": "Τρόπος παράδοσης & διδακτικές μέθοδοι",
            "bibliography_material": "Βιβλιογραφία - Εκπαιδευτικό υλικό",
            "learning_outcomes": "Μαθησιακά αποτελέσματα",
            "assessment_methods_criteria": "Μέθοδοι και κριτήρια αξιολόγησης",
        }

    parts = []
    for idx, course_plan in enumerate(course_plans, start=1):
        course_name = normalize_source_text(getattr(course_plan.course, "name", "") or "")
        parts.append(f"{course_label} {idx}: {course_name}")
        for field_name, label in labels.items():
            content = normalize_source_text(getattr(course_plan, field_name, "") or "")
            parts.append(f"{label}: {content}")
        parts.append("")

    return "\n".join(parts).strip()


def upsert_course_plan_embeddings(profile, profile_text, language, model):
    CoursePlanEmbedding.objects.filter(profile=profile).delete()
    embedding_vector = generate_embedding(profile_text, model)
    if embedding_vector:
        CoursePlanEmbedding.objects.create(
            profile=profile,
            model_name=model,
            language=language,
            vector=embedding_vector,
        )
        return True
    return False


def process_phd_ai_job(application_id, submission_id=None, user_id=None, progress_label=None):
    application = Application.objects.select_related("phd_degree").filter(id=application_id).first()
    if not application:
        return {"status": "not_found", "application_id": application_id}
    degree = application.phd_degree
    if not degree or not application.phd_title or not application.phd_abstract:
        return {"status": "skipped", "application_id": application_id}

    if submission_id and user_id and progress_label:
        set_submission_progress_safe(
            submission_id,
            user_id,
            78,
            progress_label,
            detail="AI processing",
        )

    embedding_model = "text-embedding-3-small"
    detect_text = "\n".join(
        [
            application.phd_title or "",
            application.phd_abstract or "",
            ", ".join(application.phd_keywords or []),
        ]
    ).strip()
    detected_language = detect_language(detect_text, model=None)

    if detected_language == "en":
        abstract_en = application.phd_abstract
        keywords_en = application.phd_keywords or []
        title_en = application.phd_title or ""
        profile_text_en = build_phd_profile_text(
            title_en,
            abstract_en,
            keywords_en,
            "en",
        )
        title_gr = ""
        abstract_gr = ""
        keywords_gr = []
        profile_text_gr = ""
        embedding_profile_text = profile_text_en
    else:
        abstract_gr = application.phd_abstract
        keywords_gr = application.phd_keywords or []
        title_gr = application.phd_title or ""
        profile_text_gr = build_phd_profile_text(
            title_gr,
            abstract_gr,
            keywords_gr,
            "gr",
        )
        title_en = ""
        abstract_en = ""
        keywords_en = []
        profile_text_en = ""
        embedding_profile_text = profile_text_gr

    phd_profile, _ = PhdProfile.objects.get_or_create(phd_degree=degree)
    phd_profile.title = title_gr
    phd_profile.abstract = abstract_gr
    phd_profile.keywords = keywords_gr
    phd_profile.profile_text = profile_text_gr
    phd_profile.title_en = title_en
    phd_profile.abstract_en = abstract_en
    phd_profile.keywords_en = keywords_en
    phd_profile.profile_text_en = profile_text_en
    phd_profile.original_language = detected_language
    phd_profile.save()

    embedding_created = upsert_phd_embeddings(
        degree,
        embedding_profile_text,
        detected_language,
        embedding_model,
    )
    if not embedding_created:
        raise RuntimeError("Αποτυχία δημιουργίας embedding για το διδακτορικό.")

    return {"status": "ok", "application_id": application_id}


def process_course_plan_ai_job(application_id, submission_id=None, user_id=None, progress_label=None):
    application = Application.objects.select_related("position", "position__scientific_field").filter(id=application_id).first()
    if not application:
        return {"status": "not_found", "application_id": application_id}

    course_plans = list(
        CoursePlan.objects.filter(application=application)
        .select_related("course")
        .order_by("course_id")
    )
    if not course_plans:
        return {"status": "skipped", "application_id": application_id}

    if submission_id and user_id and progress_label:
        set_submission_progress_safe(
            submission_id,
            user_id,
            78,
            progress_label,
            detail="AI processing",
        )

    detect_text = "\n".join(
        [
            normalize_source_text(getattr(cp.course, "name", "") or "")
            for cp in course_plans
        ]
        + [
            normalize_source_text(getattr(cp, "general_description", "") or "")
            for cp in course_plans
        ]
    ).strip()
    detected_language = detect_language(detect_text, model=None)
    profile_text = build_course_plan_profile_text(course_plans, detected_language)

    profile, _ = CoursePlanProfile.objects.get_or_create(application=application)
    profile.profile_text = profile_text
    profile.original_language = detected_language
    profile.save()

    embedding_model = "text-embedding-3-small"
    embedding_created = upsert_course_plan_embeddings(
        profile,
        profile_text,
        detected_language,
        embedding_model,
    )
    if not embedding_created:
        raise RuntimeError("Αποτυχία δημιουργίας embedding για το σχεδιάγραμμα μαθήματος.")

    return {"status": "ok", "application_id": application_id}


def process_scientific_field_ai_job(scientific_field_id, source_text=None):
    sf = ScientificField.objects.filter(id=scientific_field_id).first()
    if not sf:
        return {"status": "not_found", "scientific_field_id": scientific_field_id}

    if not source_text:
        courses = list(
            Course.objects.filter(scientific_field=sf).values("name", "description")
        )
        lines = [f"Scientific Field: {normalize_source_text(sf.name)}"]
        for idx, course in enumerate(courses, start=1):
            course_name = normalize_source_text(course.get("name"))
            description = normalize_source_text(course.get("description"))
            lines.extend(
                [
                    "",
                    f"Course {idx}: {course_name}",
                    f"Course Description {idx}:",
                    description,
                ]
            )
        source_text = "\n".join(lines).strip()

    model = "gpt-4.1"
    logger.info("Generating keywords/translation for scientific field %s", sf.id)
    source_text_en = translate_source_text(source_text, model)
    keywords_gr, keywords_en = extract_keywords_bilingual(source_text, model)
    logger.info(
        "Generated keywords for scientific field %s (gr=%s, en=%s)",
        sf.id,
        len(keywords_gr),
        len(keywords_en),
    )

    profile_text = source_text
    if keywords_gr:
        profile_text = f"{source_text}\n\nKeywords:\n{', '.join(keywords_gr)}"

    profile_text_en = source_text_en
    if source_text_en and keywords_en:
        profile_text_en = f"{source_text_en}\n\nKeywords:\n{', '.join(keywords_en)}"

    profile, _ = ScientificFieldProfile.objects.get_or_create(scientific_field=sf)
    profile.source_text = source_text
    profile.source_text_en = source_text_en
    profile.profile_text = profile_text
    profile.profile_text_en = profile_text_en
    profile.keywords = keywords_gr
    profile.keywords_en = keywords_en
    profile.save()

    upsert_scientific_field_embeddings(
        sf,
        profile_text,
        profile_text_en,
        "text-embedding-3-small",
    )

    return {"status": "ok", "scientific_field_id": scientific_field_id}
