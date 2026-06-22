# =============================
# IMPORTS
# =============================
import streamlit as st
import pandas as pd
import numpy as np
import re
import random
from collections import defaultdict
from datetime import datetime
from report_generator import generate_report
from ppt_generator import generate_ppt_report
import google.generativeai as genai

# =============================
# GEMINI SETUP (SAFE)
# =============================
api_key = st.secrets.get("GEMINI_API_KEY", None)

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-flash-preview")
else:
    model = None
    st.warning("⚠️ Gemini API key not found. AI features disabled.")

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="SDO Masbate City Project DESA", layout="wide")

st.image("logo.gif", use_column_width=True)
st.title("SDO Masbate City Project DESA")
st.markdown("Designed for faster data analysis and interpretation of evaluation results.")

# =============================
# CONSTANTS
# =============================
EXCLUDED_CATEGORIES = [
    "response", "department", "submitted on:", "course",
    "group", "id", "full name", "username", "institution"
]

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
# AI FUNCTIONS
# =============================
def generate_summary(text_list):
    if model is None:
        return "AI not configured."

    combined_text = "\n---\n".join(text_list[:50])

    prompt = f"""
    Summarize responses into 3–5 themes (bullet points).
    Include positive and areas for improvement.

    Responses:
    {combined_text}
    """

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

def generate_qualitative_analysis(responses):
    if model is None:
        return "AI not configured."

    if not responses:
        return "No responses available."

    sample_size = min(len(responses), 80)
    sampled = random.sample(responses, sample_size)

    combined_text = "\n---\n".join(sampled)

    prompt = f"""
    ANALYSIS and RECOMMENDATIONS.

    Responses:
    {combined_text}
    """

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

def generate_ai_narrative(training_title, context_text):
    if model is None:
        return "AI not configured."

    prompt = f"""
    Training: {training_title}

    {context_text}

    Write:
    - Analysis (~100 words)
    - Recommendations (~100 words)
    """

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

# =============================
# FILE UPLOAD
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

        qual_map = detect_strict_qualitative_columns(df)

        for label, cols in qual_map.items():
            for col in cols:
                qualitative_results[label].extend(
                    df[col].dropna().astype(str).tolist()
                )

# =============================
# COMBINED QUALITATIVE
# =============================
all_qualitative_responses = []
for r in qualitative_results.values():
    all_qualitative_responses.extend(r)

if all_qualitative_responses:
    st.subheader("📋 Combined Qualitative Responses")

    st.dataframe(
        pd.DataFrame({"Responses": all_qualitative_responses}),
        use_container_width=True
    )

    if st.button("Analyze All Responses", key="all_analysis"):
        result = generate_qualitative_analysis(all_qualitative_responses)
        st.write(result)

        if "RECOMMENDATIONS:" in result:
            parts = result.split("RECOMMENDATIONS:")
            st.session_state["analysis"] = parts[0].replace("ANALYSIS:", "").strip()
            st.session_state["recommendation"] = parts[1].strip()

# =============================
# TABLES
# =============================
if daily_results:
    daily_df = pd.DataFrame(daily_results)
    daily_df["Average"] = daily_df.mean(axis=1)

    st.subheader("📊 Daily Results")
    st.dataframe(daily_df)

    overall_daily = daily_df["Average"].mean()
    st.markdown(f"### Overall Daily: {overall_daily:.2f}")

if end_program_results:
    end_df = pd.DataFrame(end_program_results)
    end_df["Average"] = end_df.mean(axis=1)

    st.subheader("📊 End Program Results")
    st.dataframe(end_df)

    overall_end = end_df["Average"].mean()
    st.markdown(f"### Overall End: {overall_end:.2f}")

if daily_results and end_program_results:
    final_rating = (overall_daily + overall_end) / 2
    st.markdown(f"## 🏆 Final Rating: {final_rating:.2f}")

# =============================
# AUTO AI ANALYSIS
# =============================
if daily_results and end_program_results:

    if "auto_done" not in st.session_state:
        if all_qualitative_responses:
            st.session_state["auto_result"] = generate_qualitative_analysis(all_qualitative_responses)
            st.session_state["auto_done"] = True

    st.markdown("## 🤖 AI Analysis")
    st.write(st.session_state.get("auto_result", ""))

# =============================
# REPORT GENERATION
# =============================
if uploaded_files:
    st.subheader("📄 Generate Report")

    title = st.text_input("Training Title")
    date = st.text_input("Date & Venue")

    if st.button("Generate Word Report"):
        data = {
            "training_title": title,
            "date": date,
            "analysis": st.session_state.get("analysis", ""),
            "recommendation": st.session_state.get("recommendation", "")
        }

        filepath = generate_report(data)

        with open(filepath, "rb") as f:
            st.download_button("Download Word", f, file_name=filepath)

# =============================
# FOOTER
# =============================

from datetime import datetime

st.divider()

col_pic, col_text = st.columns([1, 6])

with col_pic:
    st.image("samson.jpg", width=80)

with col_text:
    st.markdown(
        f"""
        **Developed by Sir Sam**   
        Project DESA • SDO Masbate City  
        © {datetime.now().year} . All rights reserved.
        """
    )
