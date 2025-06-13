# Criteria 1: Course plan relevance (0-25 points)
def calculate_course_plan_relevance_points(application):
    # Implement actual logic 
    return 0  # Placeholder
    
# Criteria 2: Course material structure (0-5 points)
def calculate_course_material_structure_points(application):
    # Implement actual logic 
    return 0  # Placeholder

# Criteria 3: Doctoral thesis relevance (0-20 points)
def calculate_thesis_relevance_points(application):
    # Implement actual logic 
    return 0  # Placeholder

# Criteria 4: Publications/conferences (0-20 points)
def calculate_paper_points(papers):
    # Calculate based on papers (already saved to DB)
    total = 0
    for paper in papers:
        if paper.quartile == "Q1":
            total += 2
        elif paper.quartile == "Q2":
            total += 2 * 0.8
        else:
            total += 2 * 0.2 
    return total

# Criteria 5: Postdoctoral work experience (0-10 points)
def calculate_work_experience_points(application):
    return min(application.work_experience, 10)

    
def calculate_points(application, papers):
    criteria1 = calculate_course_plan_relevance_points(application)
    criteria2 = calculate_course_material_structure_points(application)
    criteria3 = calculate_thesis_relevance_points(application)
    criteria4 = calculate_paper_points(papers)
    criteria5 = calculate_work_experience_points(application)
    total = criteria1 + criteria2 + criteria3 + criteria4 + criteria5

    criteria6_bonus = total * 0.2 if application.has_not_participated_in_past_program else 0
    final_points = total + criteria6_bonus

    return {
        "course_plan_relevance_points": criteria1,
        "course_material_structure_points": criteria2,
        "thesis_relevance_points": criteria3,
        "paper_points": criteria4,              
        "work_experience_points": criteria5,
        "not_past_program_points": criteria6_bonus,
        "total_points": final_points,
    }
