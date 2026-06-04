# =============================
# IMPORTS
# =============================
import streamlit as st
import pandas as pd
import numpy as np
import re
import os
from collections import defaultdict
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from report_generator import generate_report
import tempfile
import google.generativeai as genai

# ✅ Gemini setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3-flash-preview")


# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="SDO Masbate City Project DESA", layout="wide")

st.image("logo.png", width=1200)
st.title("SDO Masbate City Project DESA")
st.markdown("Designed for faster data analysis and interpretation of evaluation results.")
st.markdown(Upload the Daily Evaluations or the End-of-Program Evaluation to get the results of each. You can upload at once the files to get analysis and recommendations.")

# =============================
# CONSTANTS
# =============================
EXCLUDED_CATEGORIES = ["response", "department", "submitted on:", "Course", "group", "ID", "Full name", "Username", "institution",]

QUAL_HEADER_PATTERNS = {
    "Insights": r"^Q\d+[_\- ]*Insights$",
    "Most Significant Learning": r"^Q\d+[_\- ]*Most[ _\-]*Significant[ _\-]*Learning$",
    "Learnings": r"^Q\d+[_\- ]*Learnings?$",
    "Suggestions": r"^Q\d+[_\- ]*Suggestions?$"
}

# =============================
# HELPERS
# =============================
def load_any_file(uploaded_file):
    try:
        return pd.read_excel(uploaded_file, engine="openpyxl")
    except:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)

def detect_rating_columns(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if "id" not in c.lower()]

def extract_category(col):
    return col.split("->")[0].strip()

def detect_strict_qualitative_columns(df):
    found = defaultdict(list)
    for col in df.columns:
        for label, pattern in QUAL_HEADER_PATTERNS.items():
            if re.match(pattern, col.strip(), flags=re.IGNORECASE):
                found[label].append(col)
    return found

# =============================
# GEMINI AI RESPONSE SUMMARIZER 
# =============================

import google.generativeai as genai

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def generate_summary(text_list):
    combined_text = "\n---\n".join(text_list[:50])  # limit for safety

    prompt = (
        "Summarize the following survey responses into 3 to 5 concise themes. "
        "Each theme should be written as a short bullet point (1–2 sentences only). "
        "Group the summarized responses into Positive Feedback and Needs Improvement. "
        "If the responses are from Most Significant Learning, Learnings, or Suggestions columns, summarize only the responses into 3 to 5 concise themes. "
        "Include direct quotation from the responses if possible. "
        "Develop also analysis and recommendations. "
        "Do not include subcategories, analysis, or explanations.\n\n"
        f"Responses:\n{combined_text}"
    )

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"


# =============================
# GEMINI AI REPORT GENERATOR 
# =============================

def generate_ai_narrative(training_title, context_text):
    prompt = f"""
    You are an educational evaluator.

    Training Program: {training_title}

    Based on the following evaluation results:
    {context_text}

    Write:
    1. A short analysis of responses of about 100 words
    2. Recommendations of about 100 words

    Include:
    - strengths
    - areas for improvement
    - overall assessment

    Keep it very concise and formal for DepEd reporting.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def generate_qualitative_analysis(responses):
    combined_text = "\n---\n".join(responses[:80])  # safe limit

    prompt = f"""
    Based on the following participant responses:

    {combined_text}

    1. Make a short analysis of these responses.
       Include strengths and weaknesses.

    2. Make a short summary of recommendations based from the responses.

    Format:

    ANALYSIS:
    ...

    RECOMMENDATIONS:
    ...
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# --- Streamlit UI ---

# =============================
# FILE UPLOADER
# =============================
uploaded_files = st.file_uploader(
    "Upload evaluation files",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

daily_results = {}
end_program_results = {}
qualitative_results = defaultdict(list)


# =============================
# PROCESS FILES
# =============================
if uploaded_files:
    for f in uploaded_files:
        df = load_any_file(f)
        st.success(f"Loaded {f.name}")

        rating_cols = detect_rating_columns(df)

        if rating_cols:
            cat_df = pd.DataFrame({
                "Category": [extract_category(c) for c in rating_cols],
                "Rating": [df[c].replace(-999, pd.NA).mean() for c in rating_cols]
            })

            cat_df = cat_df[~cat_df["Category"].str.lower().isin(EXCLUDED_CATEGORIES)]
            cat_avg = cat_df.groupby("Category", as_index=False).mean()

            if "Daily" in f.name:
                daily_results[f.name] = cat_avg.set_index("Category")["Rating"]
            elif "End" in f.name:
                end_program_results[f.name] = cat_avg.set_index("Category")["Rating"]

        # ✅ qualitative must ALSO be inside the loop
        qual_map = detect_strict_qualitative_columns(df)

        for label, cols in qual_map.items():
            for col in cols:
                qualitative_results[label].extend(
                    df[col].dropna().astype(str).tolist()
                )

# =============================
# COMBINED QUALITATIVE DATA
# =============================
all_qualitative_responses = []

for responses in qualitative_results.values():
    all_qualitative_responses.extend(responses)

                
# =============================
# DAILY EVALUATION TABLE
# =============================
if daily_results:
    st.subheader("📊 Daily Evaluation Results")

    daily_df = pd.DataFrame(daily_results)
    daily_df["Average Rating"] = daily_df.mean(axis=1)

    st.dataframe(daily_df, use_container_width=True)

    overall_daily = daily_df["Average Rating"].mean()
    st.markdown(f"### ✅ Overall Daily Evaluation Rating: {overall_daily:.2f}")

# =============================
# END OF PROGRAM TABLE
# =============================
if end_program_results:
    st.subheader("📊 End-of-Program Evaluation Results")

    end_df = pd.DataFrame(end_program_results)
    end_df["Average Rating"] = end_df.mean(axis=1)

    st.dataframe(end_df, use_container_width=True)

    overall_end = end_df["Average Rating"].mean()
    st.markdown(f"### ✅ Overall End-of-Program Rating: {overall_end:.2f}")

# ✅ FINAL OVERALL RESULT
if daily_results and end_program_results:
    final_rating = (overall_daily + overall_end) / 2
    st.markdown(f"## 🏆 Overall DESA Rating: {final_rating:.2f}")

# ✅ QUALITATIVE RESPONSES (SEPARATE)

for label, responses in qualitative_results.items():
    if responses:
        st.markdown(f"### {label}")
        st.dataframe(pd.DataFrame({label: responses}), use_container_width=True)

        if st.button(f"Analyze {label}", key=f"{label}_analysis"):
            with st.spinner("Analyzing..."):
                result = generate_summary(responses)

            st.markdown("#### 🤖 Thematic Analysis")
            st.write(result)
    
# =============================
# REPORT GENERATOR UI
# =============================
st.subheader("📊 Generate Form 5")

training_title = st.text_input("Title of Training Program")
date = st.text_input("Date and Venue")
learning_service_provider = st.text_input("Learning Service Provider/Division")
learning_areas = st.text_input("Learning Areas")
number_of_teaching_participants = st.number_input(
    "Number of Teaching Participants", min_value=0, step=1
)

number_of_non_teaching_participants = st.number_input(
    "Number of Non-Teaching Participants", min_value=0, step=1
)

number_of_teaching_related_participants = st.number_input(
    "Number of Teaching Related Participants", min_value=0, step=1
)


# ✅ GENERATE AI NARRATIVE
if st.button("Generate Form 5"):
    if all([
    training_title,
    date,
    learning_service_provider,
    learning_areas,
    number_of_teaching_participants,
    number_of_non_teaching_participants,
    number_of_teaching_related_participants
]):

        context_text = f"""
        Date and Venue: {date}
        Provider: {learning_service_provider}
        Learning Areas: {learning_areas}
        Number of Teaching Participants: {number_of_teaching_participants}
        Number of Non-Teaching Participants: {number_of_non_teaching_participants}
        Number of Teaching Related Participants: {number_of_teaching_related_participants}
        """

        narrative = generate_ai_narrative(training_title, context_text)

        # ✅ Split AI output
        analysis = ""
        recommendation = ""

        if "Recommendation" in narrative:
            parts = narrative.split("Recommendation")
            analysis = parts[0].replace("Analysis", "").strip()
            recommendation = parts[1].strip()
        else:
            analysis = narrative

        # ✅ SAVE VALUES
        st.session_state["analysis"] = analysis
        st.session_state["recommendation"] = recommendation
        st.session_state["narrative"] = narrative

        st.write("### 🤖 AI Narrative")
        st.write(narrative)

        learning_areas,
        number_of_teaching_participants,




# ✅ GENERATE REPORT
    st.subheader("📊 Generate Report")
    data = {
        "training_title": training_title,
        "date": date,
        "learning_service_provider": learning_service_provider,
        "learning_areas": learning_areas,
        "teaching": number_of_teaching_participants,
        "non_teaching": number_of_non_teaching_participants,
        "teaching_related": number_of_teaching_related_participants,

        # ✅ averages
        "daily_general_average": round(overall_daily, 2) if 'overall_daily' in locals() else "N/A",
        "end_of_program_average": round(overall_end, 2) if 'overall_end' in locals() else "N/A",
        "overall_results": round(final_rating, 2) if 'final_rating' in locals() else "N/A",

        # ✅ AI outputs
        "analysis": st.session_state.get("analysis", ""),
        "recommendation": st.session_state.get("recommendation", "")
    }

    filepath = generate_report(data)

    st.success("✅ Report Generated!")

    with open(filepath, "rb") as file:
        st.download_button(
            "📥 Download Form 5",
            file,
            file_name=filepath
        )

# =============================
# QUALITATIVE RESPONSES
# =============================
has_daily = len(daily_results) > 0
has_end = len(end_program_results) > 0
# ✅ CASE 1: BOTH Daily + End → AUTOMATIC AI MODE
if has_daily and has_end:

    for label, responses in qualitative_results.items():
        if responses:
            st.markdown(f"### {label}")
            st.dataframe(pd.DataFrame({label: responses}), use_container_width=True)

    # ✅ AUTO AI ANALYSIS
    if all_qualitative_responses:
        with st.spinner("Generating AI Analysis..."):
            ai_result = generate_qualitative_analysis(all_qualitative_responses)

        st.markdown("## 🤖 AI Analysis & Recommendations")
        st.write(ai_result)

        # ✅ SPLIT AI OUTPUT
        analysis = ""
        recommendation = ""

        if "RECOMMENDATIONS:" in ai_result:
            parts = ai_result.split("RECOMMENDATIONS:")
            analysis = parts[0].replace("ANALYSIS:", "").strip()
            recommendation = parts[1].strip()
        else:
            analysis = ai_result

        # ✅ SAVE FOR REPORT
        st.session_state["analysis"] = analysis
        st.session_state["recommendation"] = recommendation


# ✅ CASE 2: ONLY ONE TYPE → KEEP YOUR OLD SYSTEM
else:
    for label, responses in qualitative_results.items():
        if responses:
            st.markdown(f"### {label}")
            st.dataframe(pd.DataFrame({label: responses}), use_container_width=True)

            if st.button(f"Analyze {label}", key=f"{label}_section2"):
                with st.spinner("Analyzing..."):
                    result = generate_summary(responses)

                st.markdown("#### 🤖 Thematic Analysis")
                st.write(result)

# =============================
# FOOTER
# =============================

from datetime import datetime

st.divider()

col_pic, col_text = st.columns([1, 6])

with col_pic:
    st.image("samson.png", width=80)

with col_text:
    st.markdown(
        f"""
        **Developed by Sir Sam**   
        Project DESA • SDO Masbate City  
        © {datetime.now().year} . All rights reserved.
        """
    )

