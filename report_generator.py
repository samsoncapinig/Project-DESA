from docxtpl import DocxTemplate
import os
from datetime import datetime

def generate_report(data):
    template_path = "desa_template.docx"

    doc = DocxTemplate(template_path)

    context = {
        "Title of Training Program": data["training_title"],
        "date": datetime.now().strftime("%B %d, %Y"),
        "Learning Service Provider": data["learning_service_provider"],
        "Teaching": data["teaching"],
        "Non-Teaching": data["non_teaching"],
        "Teaching Related": data["teaching_related"],
        "Result of Daily Online Evaluation": data["daily_general_average"],
        "Result of End-of-Program Evaluation": data["end_of_program_average"],
        "Overall Result": data["overall_results"],
        "Analysis": data["analysis"],
        "Recommendation": data["recommendation"]
    }

    doc.render(context)

    filename = f"DESA_Report_{data['school_name'].replace(' ', '_')}.docx"

    # IMPORTANT for Streamlit Cloud: save in memory-safe path
    filepath = filename
    doc.save(filepath)

    return filepath
``
