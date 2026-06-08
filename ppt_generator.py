from pptx import Presentation
from pptx.util import Inches, Pt
from datetime import datetime
import os

def generate_ppt_report(data, rating_data):
    """
    Generate PowerPoint report from template with evaluation data.
    
    Args:
        data: Dictionary with basic training info
        rating_data: Dictionary with category ratings from evaluation files
    """
    
    template_path = "desa_template.pptx.pptx"
    
    # Load the template
    prs = Presentation(template_path)
    
    # Extract averages from rating_data
    # rating_data structure: {category: average_score}
    
    administrative_arrangement = rating_data.get("Administrative Arrangements", "N/A")
    food = rating_data.get("Food/Meal", "N/A")
    program_management = rating_data.get("Program Management", "N/A")
    training_venue = rating_data.get("Training Venue", "N/A")
    
    # Session averages - sum of all Day1_LM sessions
    session_ratings = [v for k, v in rating_data.items() if "day" in k.lower() and "lm" in k.lower()]
    average_rating_of_sessions = sum(session_ratings) / len(session_ratings) if session_ratings else 0
    
    # Overall daily average
    overall_daily_average = data.get("daily_general_average", 0)
    
    # End of program evaluation averages
    program_management1 = rating_data.get("Program Management", "N/A")
    attainment_of_objectives = rating_data.get("Attainment of Objectives", "N/A")
    delivery_of_content = rating_data.get("Delivery of Content", "N/A")
    provision_of_support_materials = rating_data.get("Provision of Support Materials", "N/A")
    program_management_team1 = rating_data.get("Program Management Team", "N/A")
    training_venue1 = rating_data.get("Training Venue", "N/A")
    food1 = rating_data.get("Food", "N/A")
    
    # Session evaluation ratings (individual)
    day1_lm1 = rating_data.get("Day1_LM1", "N/A")
    day1_lm2 = rating_data.get("Day1_LM2", "N/A")
    day1_lm3 = rating_data.get("Day1_LM3", "N/A")
    day1_lm4 = rating_data.get("Day1_LM4", "N/A")
    day1_lm5 = rating_data.get("Day1_LM5", "N/A")
    
    # Analysis and recommendation
    analysis = data.get("analysis", "")
    recommendation = data.get("recommendation", "")
    
    # Summary ratings
    daily_general_average = data.get("daily_general_average", 0)
    end_of_program_average = data.get("end_of_program_average", 0)
    overall_results = data.get("overall_results", 0)
    
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
        _replace_text_in_slide(slide2, {
            "{{administrative_arrangement}}": _format_value(administrative_arrangement),
            "{{food}}": _format_value(food),
            "{{program_management}}": _format_value(program_management),
            "{{training_venue}}": _format_value(training_venue),
            "{{average_rating_of_sessions}}": _format_value(average_rating_of_sessions),
            "{{overall_daily_average}}": _format_value(overall_daily_average),
        })
    
    # ===== SLIDE 3: END-OF-PROGRAM EVALUATION =====
    if len(prs.slides) > 2:
        slide3 = prs.slides[2]
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
            "{{analysis}}": analysis,
        })
    
    # ===== SLIDE 10: RECOMMENDATION =====
    if len(prs.slides) > 9:
        slide10 = prs.slides[9]
        _replace_text_in_slide(slide10, {
            "{{recommendation}}": recommendation,
        })
    
    # ===== SLIDE 11: SUMMARY RATINGS =====
    if len(prs.slides) > 10:
        slide11 = prs.slides[10]
        _replace_text_in_slide(slide11, {
            "{{daily_general_average}}": _format_value(daily_general_average),
            "{{end_of_program_average}}": _format_value(end_of_program_average),
            "{{overall_results}}": _format_value(overall_results),
        })
    
    # Save the presentation
    filename = f"DESA_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    prs.save(filename)
    
    return filename


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
