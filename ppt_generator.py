from pptx import Presentation
from datetime import datetime
import re


# ===== NORMALIZE FUNCTION =====
def _normalize(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower().replace("_", " "))


# ===== MAIN FUNCTION =====
def generate_ppt_report(data, daily_rating_data, end_rating_data):

    prs = Presentation("desa_template.pptx")

    # ===== SLIDE 1 =====
    if len(prs.slides) > 0:
        slide1 = prs.slides[0]
        _replace_text_in_slide(slide1, {
            "{{title}}": data.get("training_title", ""),
            "{{date}}": data.get("date", ""),
            "{{venue}}": data.get("venue", ""),
            "{{program_owner}}": data.get("program_owner", ""),
        })

    # ===== SLIDE 2 =====
    if len(prs.slides) > 1:
        slide2 = prs.slides[1]

        program_management = _find_matching_value(daily_rating_data, ["program", "management"])
        accommodation = _find_matching_value(daily_rating_data, ["accommodation"])
        training_venue = _find_matching_value(daily_rating_data, ["training", "venue"])
        food = _find_matching_value(daily_rating_data, ["food"])
        administrative_arrangements = _find_matching_value(daily_rating_data, ["administrative"])

        # ✅ Auto-detect averages
        avg_values = _extract_average_ratings(daily_rating_data)
        avg_sessions = sum(avg_values) / len(avg_values) if avg_values else 0

        _replace_text_in_slide(slide2, {
            "{{program_management}}": _format_value(program_management),
            "{{accommodation}}": _format_value(accommodation),
            "{{training_venue}}": _format_value(training_venue),
            "{{food}}": _format_value(food),
            "{{administrative_arrangements}}": _format_value(administrative_arrangements),
            "{{overall_daily_average}}": _format_value(avg_sessions),
        })

    # ===== SLIDE 3 =====
    if len(prs.slides) > 2:
        slide3 = prs.slides[2]

        # ✅ Auto-detect end averages
        end_values = _extract_average_ratings(end_rating_data)
        end_avg = sum(end_values) / len(end_values) if end_values else 0

        replacements = {
            "{{program_management1}}": _format_value(_find_matching_value(end_rating_data, ["program", "management"])),
            "{{attainment_of_objectives}}": _format_value(_find_matching_value(end_rating_data, ["attainment"])),
            "{{delivery_of_content}}": _format_value(_find_matching_value(end_rating_data, ["delivery", "content"])),
            "{{provision_of_support_materials}}": _format_value(_find_matching_value(end_rating_data, ["support", "materials"])),
            "{{program_management_team}}": _format_value(_find_matching_value(end_rating_data, ["program", "team"])),
            "{{training_venue1}}": _format_value(_find_matching_value(end_rating_data, ["training", "venue"])),
            "{{food1}}": _format_value(_find_matching_value(end_rating_data, ["food"])),
            "{{accommodation1}}": _format_value(_find_matching_value(end_rating_data, ["accommodation"])),

            # ✅ FIXED
            "{{end_of_program_average}}": _format_value(end_avg),
        }

        _replace_text_in_slide(slide3, replacements)

    # ===== SAVE FILE =====
    filename = f"DESA_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    prs.save(filename)

    return filename


# ===== HELPERS =====

def _find_matching_value(data_dict, keywords):
    if not data_dict:
        return "N/A"

    keywords = [_normalize(k) for k in keywords]

    best_match = None

    for key, value in data_dict.items():
        key_clean = _normalize(key)
        match_count = sum(1 for k in keywords if k in key_clean)

        if match_count > 0:
            if best_match is None or match_count > best_match[1]:
                best_match = (value, match_count)

    return best_match[0] if best_match else "N/A"


def _replace_text_in_slide(slide, replacements):
    for shape in slide.shapes:

        if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                text = "".join(run.text for run in paragraph.runs)

                for placeholder, value in replacements.items():
                    text = text.replace(placeholder, str(value))

                paragraph.text = text

        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    text = cell.text

                    for placeholder, value in replacements.items():
                        text = text.replace(placeholder, str(value))

                    cell.text = text


def _extract_average_ratings(data_dict):
    if not data_dict:
        return []

    avg_values = []

    for key, value in data_dict.items():
        key_clean = key.lower()

        if "average" in key_clean or "avg" in key_clean:
            if isinstance(value, (int, float)):
                avg_values.append(float(value))

        elif any(cat in key_clean for cat in [
            "program", "accommodation", "venue", "food",
            "administrative", "attainment", "delivery", "support", "team"
        ]):
            if isinstance(value, (int, float)):
                avg_values.append(float(value))

    return avg_values


def _format_value(value):
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value) if value else "N/A"
