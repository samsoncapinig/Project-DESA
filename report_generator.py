from docxtpl import DocxTemplate
from datetime import datetime

def generate_report(data):
    template_path = "desa_template.docx"

    doc = DocxTemplate(template_path)

    context = {
        # ✅ MATCH YOUR TEMPLATE VARIABLES EXACTLY
        "training_title": data.get("training_title", ""),
        "date": data.get("date", datetime.now().strftime("%B %d, %Y")),
        "learning_service_provider": data.get("learning_service_provider", ""),
        "learning_areas": data.get("learning_areas", ""),
        "teaching": data.get("teaching", ""),
        "non_teaching": data.get("non_teaching", ""),
        "teaching_related": data.get("teaching_related", ""),
        "narrative": data.get("narrative", ""),

        # OPTIONAL SAFE FIELDS
        "daily_general_average": data.get("daily_general_average", "N/A"),
        "end_of_program_average": data.get("end_of_program_average", "N/A"),
        "overall_results": data.get("overall_results", "N/A"),
        "analysis": data.get("analysis", ""),
        "recommendation": data.get("recommendation", "")
    }

    doc.render(context)

    # ✅ SAFE filename (no missing key)
    filename = f"DESA_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    doc.save(filename)

    return filename

Paragraph("Analysis", styles["Heading2"]),
Paragraph(data["analysis"], styles["Normal"]),

Paragraph("Recommendations", styles["Heading2"]),
Paragraph(data["recommendation"], styles["Normal"]),
