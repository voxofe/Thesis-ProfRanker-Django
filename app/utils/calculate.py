
import logging
import math
import re

from app.models import CoursePlan, PhdProfile

logger = logging.getLogger(__name__)


def _criterion1_trace(message, *args):
    # Use print so traces are visible in the Django development server console
    # even when logging level filters out DEBUG records.
    if args:
        print(message % args)
    else:
        print(message)


def _criterion2_trace(message, *args):
    # Use print so traces are visible in the Django development server console
    # even when logging level filters out DEBUG records.
    if args:
        print(message % args)
    else:
        print(message)


def cosine_similarity(vec_a, vec_b):
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for idx, value in enumerate(vec_a):
        dot += value * vec_b[idx]
        norm_a += value * value
        norm_b += vec_b[idx] * vec_b[idx]
    if norm_a == 0 or norm_b == 0:
        return None
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def custom_round(value):
    """
    Custom rounding function:
    - 0.1-0.4 rounds down to the nearest integer
    - 0.5-0.9 rounds up to the nearest integer
    """
    decimal = value - int(value)    
    if decimal >= 0.5:
        value = int(value) + 1
    else:
        value = int(value)
    return value


def _word_count(text):
    return len([w for w in re.split(r"\s+", str(text or "").strip()) if w])


def _token_set(text):
    tokens = re.findall(r"[\w\u0370-\u03ff\u1f00-\u1fff]+", str(text or "").lower())
    return {token for token in tokens if len(token) > 2}


def _jaccard_similarity(text_a, text_b):
    set_a = _token_set(text_a)
    set_b = _token_set(text_b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return inter / union


def _schedule_item_count(text):
    normalized = str(text or "")
    # Count likely item boundaries: numbered lists, newlines, semicolons, bullet marks.
    numbered = re.findall(r"(?:^|\s)(?:\d+\.|\d+\)|\d+[:\-])", normalized)
    line_items = [line.strip() for line in normalized.splitlines() if line.strip()]
    delimiter_items = [part.strip() for part in re.split(r"[;•·]+", normalized) if part.strip()]
    return max(len(numbered), len(line_items), len(delimiter_items))


# Criteria 1: Course plan relevance (0-25 points)
def calculate_course_plan_relevance_points(application):
    position = application.position
    if not position or not position.scientific_field_id:
        return 0, None

    course_plans = list(CoursePlan.objects.filter(application=application).select_related("course", "profile"))
    if not course_plans:
        return 0, None

    per_course_similarities = []
    app_id = getattr(application, "id", "?")
    username = getattr(getattr(application, "user", None), "username", "unknown")

    for course_plan in course_plans:
        try:
            profile = course_plan.profile
        except Exception:
            return 0, None

        preferred_language = profile.original_language or "gr"

        def select_language(lang):
            if not profile.profile_text:
                return None

            course_plan_embedding = (
                profile.embeddings.filter(language=lang).order_by("-created_at").first()
            )
            if not course_plan_embedding:
                return None

            course_embedding = (
                course_plan.course.embeddings.filter(
                    language=lang,
                    model_name=course_plan_embedding.model_name,
                )
                .order_by("-created_at")
                .first()
            )
            if not course_embedding:
                return None

            return {
                "course_plan_embedding": course_plan_embedding,
                "course_embedding": course_embedding,
            }

        selected = select_language(preferred_language)
        selected_language = preferred_language
        if not selected:
            fallback_language = "en" if preferred_language == "gr" else "gr"
            selected = select_language(fallback_language)
            selected_language = fallback_language
        if not selected:
            _criterion1_trace(
                "[criterion1 app=%s user=%s course=%s] FAIL no-embedding-match preferred=%s",
                app_id,
                username,
                getattr(course_plan, "course_id", "?"),
                preferred_language,
            )
            return 0, None

        cp_vector = selected["course_plan_embedding"].vector
        course_vector = selected["course_embedding"].vector
        if cp_vector is None or course_vector is None:
            return 0, None

        cp_vector = list(cp_vector)
        course_vector = list(course_vector)
        if len(cp_vector) != len(course_vector):
            return 0, None
        if any(v is None for v in cp_vector) or any(v is None for v in course_vector):
            return 0, None

        similarity = cosine_similarity(cp_vector, course_vector)
        if similarity is None:
            return 0, None

        course_name = getattr(getattr(course_plan, "course", None), "name", "") or "(no-name)"
        cp_text = getattr(profile, "profile_text", "") or ""
        course_profile = getattr(getattr(course_plan, "course", None), "profile", None)
        course_text = getattr(course_profile, "profile_text", "") if course_profile else ""
        cp_words = _word_count(cp_text)
        course_words = _word_count(course_text)
        jaccard = _jaccard_similarity(cp_text, course_text)
        _criterion1_trace(
            "[criterion1 app=%s user=%s course=%s name=%s] cosine=%.6f lang=%s model=%s cp_words=%d course_words=%d jaccard=%.4f",
            app_id,
            username,
            getattr(course_plan, "course_id", "?"),
            course_name,
            similarity,
            selected_language,
            selected["course_plan_embedding"].model_name,
            cp_words,
            course_words,
            jaccard,
        )

        per_course_similarities.append(similarity)

    if not per_course_similarities:
        return 0, None

    similarity = sum(per_course_similarities) / len(per_course_similarities)

    # Recalibrated mapping for criterion 1 based on observed review anchors:
    # - cosine ~0.73 should land around 17/25
    # - cosine ~0.62 should land around 9/25
    # - cosine ~0.57 should land around 3/25
    min_useful = 0.556
    max_useful = 0.871
    normalized = (similarity - min_useful) / (max_useful - min_useful)
    normalized = max(0.0, min(1.0, normalized))
    normalized = normalized ** 0.645

    points = custom_round(normalized * 25)
    _criterion1_trace(
        "[criterion1 app=%s user=%s] average_cosine=%.6f courses=%d normalized=%.6f points=%d",
        app_id,
        username,
        similarity,
        len(per_course_similarities),
        normalized,
        max(0, min(25, points)),
    )
    return max(0, min(25, points)), similarity
    
# Criteria 2: Course material structure (0-5 points)
def calculate_course_material_structure_points(application):
    # insufficient know how and resources to implement this criterion, so we will return 5 for all now
    return 5

# Criteria 3: Doctoral thesis relevance (0-20 points)
def calculate_thesis_relevance_points(application):
    phd_degree = application.phd_degree
    position = application.position
    if not phd_degree or not position or not position.scientific_field_id:
        return 0, None

    try:
        phd_profile = phd_degree.profile
    except PhdProfile.DoesNotExist:
        return 0, None

    preferred_language = phd_profile.original_language or "gr"

    def select_language(lang):
        field_profile = position.scientific_field.profiles.first()
        if not field_profile:
            return None
        phd_text = phd_profile.profile_text if lang == "gr" else phd_profile.profile_text_en
        field_text = field_profile.profile_text if lang == "gr" else field_profile.profile_text_en
        if not phd_text or not field_text:
            return None

        phd_embedding = (
            phd_degree.embeddings.filter(language=lang).order_by("-created_at").first()
        )
        if not phd_embedding:
            return None
        field_embedding = (
            position.scientific_field.embeddings.filter(language=lang, model_name=phd_embedding.model_name)
            .order_by("-created_at")
            .first()
        )
        if not field_embedding:
            return None

        return {
            "phd_embedding": phd_embedding,
            "field_embedding": field_embedding,
        }

    selected = select_language(preferred_language)
    if not selected:
        fallback_language = "en" if preferred_language == "gr" else "gr"
        selected = select_language(fallback_language)
    if not selected:
        return 0, None

    phd_vector = selected["phd_embedding"].vector
    field_vector = selected["field_embedding"].vector
    if phd_vector is None or field_vector is None:
        return 0, None
    phd_vector = list(phd_vector)
    field_vector = list(field_vector)
    if len(phd_vector) != len(field_vector):
        return 0, None
    if any(v is None for v in phd_vector) or any(v is None for v in field_vector):
        return 0, None

    similarity = cosine_similarity(phd_vector, field_vector)
    if similarity is None:
        return 0, None

    min_useful = 0.47
    max_useful = 0.82
    normalized = (similarity - min_useful) / (max_useful - min_useful)
    normalized = max(0.0, min(1.0, normalized))

    points = custom_round(normalized * 20)
    return max(0, min(20, points)), similarity

# Criteria 4: Publications/conferences (0-20 points)
def calculate_publication_points(publications):
    # Calculate based on publications (already saved to DB)
    total = 0
    count = 0
    for publication in publications:
        count += 1
        if publication.quartile == "Q1":
            total += 2
        elif publication.quartile == "Q2":
            total += 2 * 0.8
        else:
            total += 2 * 0.2 
        
        print(f"Publication {count}: {publication.publication_title} - Points: {total}")
    if total > 20:
        total = 20

    total = custom_round(total)
    print(f"Total publication points: {total}")
    return total

# Criteria 5: Postdoctoral work experience (0-10 points)
def calculate_work_experience_points(application):
    return min(application.work_experience, 10)

    
def calculate_points(application, publications):
    criteria1, course_plan_similarity = calculate_course_plan_relevance_points(application)
    criteria2 = calculate_course_material_structure_points(application)
    criteria3, similarity = calculate_thesis_relevance_points(application)
    criteria4 = calculate_publication_points(publications)
    criteria5 = calculate_work_experience_points(application)
    total = criteria1 + criteria2 + criteria3 + criteria4 + criteria5

    criteria6_bonus = total * 0.2 if application.has_not_participated_in_past_program else 0
    criteria6_bonus = custom_round(criteria6_bonus)
    final_points = total + criteria6_bonus

    return {
        "course_plan_relevance_points": criteria1,
        "course_plan_cosine_similarity": course_plan_similarity,
        "course_material_structure_points": criteria2,
        "thesis_relevance_points": criteria3,
        "phd_cosine_similarity": similarity,
        "publication_points": criteria4,              
        "work_experience_points": criteria5,
        "not_past_program_points": criteria6_bonus,
        "total_points": final_points,
    }
