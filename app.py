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

# ✅ Gemini setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3-flash-preview")

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="SDO Masbate City Project DESA", layout="wide")

st.image("logo.gif", width=1400)
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
    return col.split("->")[0].strip()   # ✅ FIXED (removed &gt;)

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
    combined_text = "\n---\n".join(text_list[:50])

    prompt = f"""
    Summarize the following responses into 3–5 concise themes.
    Group into Positive Feedback and Needs Improvement.

    Responses:
    {combined_text}
    """

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

def generate_qualitative_analysis(responses):
    sample_size = min(len(responses), 80)
    sampled = random.sample(responses, sample_size)

    prompt = f"""
    Based on responses:

    {'---'.join(sampled)}

    Provide:
    FINDINGS
    ANALYSIS
    RECOMMENDATIONS
    """

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

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
participant_summary = []

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

        # ✅ QUALITATIVE
        qual_map = detect_strict_qualitative_columns(df)
        for label, cols in qual_map.items():
            for col in cols:
                qualitative_results[label].extend(
                    df[col].dropna().astype(str).tolist()
                )

        # =============================
        # PARTICIPANT TYPE COUNT (FIXED)
        # =============================
        teaching = 0
        non_teaching = 0
        teaching_related = 0

        participant_col = None

        # ✅ FIXED INDENTATION
        for col in df.columns:
            if "description" in col.lower():
                participant_col = col
                break

        if participant_col:
            series = df[participant_col].dropna().astype(str)

            teaching_related = series.str.contains("Teaching Related", case=False).sum()
            non_teaching = series.str.contains("Non-Teaching", case=False).sum()

            teaching = (
                series.str.contains(r"\bTeaching\b", case=False, regex=True).sum()
                - teaching_related
            )

        total_participants = len(df)

        participant_summary.append({
            "File Name": f.name,
            "Teaching": teaching,
            "Non-Teaching": non_teaching,
            "Teaching Related": teaching_related,
            "Total": total_participants
        })

# =============================
# PARTICIPANT SUMMARY
# =============================
if participant_summary:
    st.subheader("👨‍🏫 Teaching vs Non-Teaching Summary")

    participant_df = pd.DataFrame(participant_summary)
    totals = participant_df[["Teaching", "Non-Teaching", "Teaching Related", "Total"]].sum()

    total_row = pd.DataFrame([{
        "File Name": "TOTAL",
        "Teaching": totals["Teaching"],
        "Non-Teaching": totals["Non-Teaching"],
        "Teaching Related": totals["Teaching Related"],
        "Total": totals["Total"]
    }])

    participant_df = pd.concat([participant_df, total_row], ignore_index=True)
    st.dataframe(participant_df, use_container_width=True)

# =============================
# DAILY RESULTS
# =============================
if daily_results:
    st.subheader("📊 Daily Evaluation Results")
    daily_df = pd.DataFrame(daily_results)
    daily_df["Average Rating"] = daily_df.mean(axis=1)

    st.dataframe(daily_df, use_container_width=True)
    overall_daily = daily_df["Average Rating"].mean()

    st.markdown(f"### ✅ Overall Daily Rating: {overall_daily:.2f}")

# =============================
# END PROGRAM
# =============================
if end_program_results:
    st.subheader("📊 End-of-Program Results")
    end_df = pd.DataFrame(end_program_results)
    end_df["Average Rating"] = end_df.mean(axis=1)

    st.dataframe(end_df, use_container_width=True)
    overall_end = end_df["Average Rating"].mean()

    st.markdown(f"### ✅ Overall End Rating: {overall_end:.2f}")

# =============================
# FINAL RATING
# =============================
if daily_results and end_program_results:
    final_rating = (overall_daily + overall_end) / 2
    st.markdown(f"## 🏆 Overall DESA Rating: {final_rating:.2f}")

# =============================
# FOOTER
# =============================
st.divider()

col_pic, col_text = st.columns([1, 6])

with col_pic:
    st.image("samson.jpg", width=80)

with col_text:
    st.markdown(f"""
    **Developed by Sir Sam**  
    Project DESA • SDO Masbate City  
    © {datetime.now().year}
    """)
