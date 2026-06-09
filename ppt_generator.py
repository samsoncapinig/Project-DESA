from pptx import Presentation
from pptx.util import Inches, Pt
from datetime import datetime
import os

def generate_ppt_report(data, daily_rating_data, end_rating_data):
    """
    Generate PowerPoint report from template with evaluation data.
    
    Args:
        data: Dictionary with basic training info
        daily_rating_data: Dictionary with daily evaluation ratings {category: average_score}
        end_rating_data: Dictionary with end-of-program evaluation ratings {category: average_score}
    """
    
    template_path = "desa_template.pptx.pptx"
    
    # Load the template
    prs = Presentation(template_path)
    
    # ===== SLIDE 1: TRAINING INFO =====
    if len(prs.slides) > 0:
        slide1 = prs.slides[0]
        _replace_text_in_slide(slide1, {
            "{{title}}": data.get("training_title", ""),
            "{{date}}": data.get("date", ""),
            "{{venue}}": data.get("venue", ""),
            "{{program_owner}}": data.get("program_owner", ""),
        })
    
    # ===== SLIDE 2: DAILY EVALUATION SUMMARY =====
    if len(prs.slides) > 1:
        slide2 = prs.slides[1]
        
        # Extract values from daily_rating_data with flexible key matching
        administrative_arrangement = _find_matching_value(daily_rating_data, ["administrative", "arrangement"])\n        food = _find_matching_value(daily_rating_data, ["food", "meal"])
        program_management = _find_matching_value(daily_rating_data, ["program", "management"])
        training_venue = _find_matching_value(daily_rating_data, ["training", "venue"])
        
        # Session averages from daily data
        session_ratings = [v for k, v in daily_rating_data.items() if _is_session_rating(k)]
        average_rating_of_sessions = sum(session_ratings) / len(session_ratings) if session_ratings else 0
        
        _replace_text_in_slide(slide2, {
            "{{administrative_arrangement}}": _format_value(administrative_arrangement),
            "{{food}}": _format_value(food),
            "{{program_management}}": _format_value(program_management),
            "{{training_venue}}": _format_value(training_venue),
            "{{average_rating_of_sessions}}": _format_value(average_rating_of_sessions),
            "{{overall_daily_average}}": _format_value(data.get("daily_general_average", 0)),
        })
    
    # ===== SLIDE 3: END-OF-PROGRAM EVALUATION =====
    if len(prs.slides) > 2:
        slide3 = prs.slides[2]
        
        # Extract values from end_rating_data with flexible key matching
        program_management1 = _find_matching_value(end_rating_data, ["program", "management"])
        attainment_of_objectives = _find_matching_value(end_rating_data, ["attainment", "objective"])
        delivery_of_content = _find_matching_value(end_rating_data, ["delivery", "content"])
        provision_of_support_materials = _find_matching_value(end_rating_data, ["provision", "support", "material"])
        program_management_team1 = _find_matching_value(end_rating_data, ["program", "management", "team"])
        training_venue1 = _find_matching_value(end_rating_data, ["training", "venue"])
        food1 = _find_matching_value(end_rating_data, ["food"])
        
        _replace_text_in_slide(slide3, {
            "{{program_management1}}": _format_value(program_management1),
            "{{attainment_of_objectives}}": _format_value(attainment_of_objectives),
            "{{delivery_of_content}}": _format_value(delivery_of_content),
            "{{provision_of_support_materials}}": _format_value(provision_of_support_materials),
            "{{program_management_team1}}": _format_value(program_management_team1),
            "{{training_venue1}}": _format_value(training_venue1),
            "{{food1}}": _format_value(food1),
        })
    
    # ===== SLIDES 4-8: SESSION EVALUATIONS =====
    # Extract session ratings from daily data
    day1_lm1 = _find_matching_value(daily_rating_data, ["day1", "lm1"])
    day1_lm2 = _find_matching_value(daily_rating_data, ["day1", "lm2"])
    day1_lm3 = _find_matching_value(daily_rating_data, ["day1", "lm3"])
    day1_lm4 = _find_matching_value(daily_rating_data, ["day1", "lm4"])
    day1_lm5 = _find_matching_value(daily_rating_data, ["day1", "lm5"])
    
    session_data = [
        ("{{day1_lm1}}", day1_lm1),
        ("{{day1_lm2}}", day1_lm2),
        ("{{day1_lm3}}", day1_lm3),
        ("{{day1_lm4}}", day1_lm4),
        ("{{day1_lm5}}", day1_lm5),
    ]
    
    for i, (placeholder, value) in enumerate(session_data):
        slide_index = 3 + i  # Slides 4-8 (indices 3-7)
        if len(prs.slides) > slide_index:
            slide = prs.slides[slide_index]
            _replace_text_in_slide(slide, {placeholder: _format_value(value)})
    
    # ===== SLIDE 9: ANALYSIS =====
    if len(prs.slides) > 8:
        slide9 = prs.slides[8]
        _replace_text_in_slide(slide9, {
            "{{analysis}}": data.get("analysis", ""),
        })
    
    # ===== SLIDE 10: RECOMMENDATION =====
    if len(prs.slides) > 9:
        slide10 = prs.slides[9]
        _replace_text_in_slide(slide10, {
            "{{recommendation}}": data.get("recommendation", ""),
        })
    
    # ===== SLIDE 11: SUMMARY RATINGS =====
    if len(prs.slides) > 10:
        slide11 = prs.slides[10]
        _replace_text_in_slide(slide11, {
            "{{daily_general_average}}": _format_value(data.get("daily_general_average", 0)),
            "{{end_of_program_average}}": _format_value(data.get("end_of_program_average", 0)),
            "{{overall_results}}": _format_value(data.get("overall_results", 0)),
        })
    
    # Save the presentation
    filename = f"DESA_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    prs.save(filename)
    
    return filename


def _find_matching_value(data_dict, keywords):
    """
    Find a value in the dictionary by matching keywords (case-insensitive, flexible).
    Returns the first match or "N/A" if no match found.
    """
    if not data_dict:
        return "N/A"
    
    for key, value in data_dict.items():
        key_lower = key.lower().replace("_", " ").replace("->", " ")
        # Check if ALL keywords are found in the key
        if all(keyword.lower() in key_lower for keyword in keywords):
            return value
    
    return "N/A"


def _is_session_rating(key):
    """Check if a key represents a session rating (e.g., Day1_LM1, Day1 LM2, etc.)"""
    key_lower = key.lower().replace("_", " ").replace("->", " ")
    return "day" in key_lower and "lm" in key_lower


def _replace_text_in_slide(slide, replacements):
    """Replace placeholders in all text boxes and shapes in a slide."""
    
    for shape in slide.shapes:
        # Handle text frames
        if hasattr(shape, "text_frame"):
            text_frame = shape.text_frame
            for paragraph in text_frame.paragraphs:
                for run in paragraph.runs:
                    for placeholder, value in replacements.items():
                        if placeholder in run.text:
                            run.text = run.text.replace(placeholder, str(value))
        
        # Handle tables
        if shape.has_table:
            table = shape.table
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.text_frame.paragraphs:
                        for run in paragraph.runs:
                            for placeholder, value in replacements.items():
                                if placeholder in run.text:
                                    run.text = run.text.replace(placeholder, str(value))


def _format_value(value):
    """Format a value for display (handle N/A and numbers)."""
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value) if value else "N/A"
