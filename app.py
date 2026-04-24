
# app.py – Evaluation Dashboard v6 (Combined Multi-Day Table)

import streamlit as st
import pandas as pd
import numpy as np
import re
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import tempfile

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="SDO Masbate City Project DESA", layout="wide")
st.image("logo.png", width=1200)
st.title("SDO Masbate City Project DESA")
st.markdown("Designed for faster data analaysis and interpretation of the Daily Evaluation and End of Program Evaluation Results for DepEd Trainings.")

st.markdown("Please click the Upload button or drag and drop to add the excel file. You can drag and drop one by one or all at once.")
# =============================
# CONSTANTS
# =============================
EXCLUDED_CATEGORIES = ["department", "group", "institution"]

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
    except Exception:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)


def detect_rating_columns(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude_keywords = ["id", "response"]
    return [c for c in numeric_cols if not any(k in c.lower() for k in exclude_keywords)]


def extract_category(col):
    return col.split("->")[0].strip() if "->" in col else col.strip()


def detect_strict_qualitative_columns(df):
    found = defaultdict(list)
    for col in df.columns:
        for label, pattern in QUAL_HEADER_PATTERNS.items():
            if re.match(pattern, col.strip(), flags=re.IGNORECASE):
                found[label].append(col)
    return found

# =============================
# FILE UPLOADER
# =============================
uploaded_files = st.file_uploader(
    "Upload CSV or Excel evaluation files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

category_results = {}
qualitative_results = defaultdict(list)

if uploaded_files:
    for f in uploaded_files:
        df = load_any_file(f)
        st.success(f"Loaded {f.name}")

        rating_cols = detect_rating_columns(df)
        if rating_cols:
            cat_df = pd.DataFrame({
                "Category": [extract_category(c) for c in rating_cols],
                "Rating": [df[c].mean() for c in rating_cols]
            })
            cat_df = cat_df[~cat_df["Category"].str.lower().isin(EXCLUDED_CATEGORIES)]
            cat_avg = cat_df.groupby("Category", as_index=False).mean()

            fname = f.name.replace(".csv", "").replace(".xlsx", "").replace(".xls", "")
            category_results[fname] = cat_avg.set_index("Category")["Rating"]

        qual_map = detect_strict_qualitative_columns(df)
        for label, cols in qual_map.items():
            for col in cols:
                qualitative_results[label].extend(df[col].dropna().astype(str).tolist())

    # =============================
    # COMBINED CATEGORY TABLE
    # =============================
    st.divider()
    st.subheader("📊 Combined Category Ratings")

    combined_df = pd.DataFrame(category_results)
    combined_df["Average Rating"] = combined_df.mean(axis=1)
    combined_df = combined_df.sort_values("Average Rating", ascending=False)

    st.dataframe(
        combined_df.reset_index().rename(columns={"index": "Category"}),
        use_container_width=True
    )

    # ✅ COMPUTE GRAND OVERALL RATING
    overall_rating = combined_df["Average Rating"].mean()

    # ✅ DISPLAY STATEMENT BELOW THE TABLE
    st.markdown(
        f"""
        ### ✅ Your Overall Rating is **{overall_rating:.2f}**
        """)
    
    # =============================
    # QUALITATIVE RESPONSES
    # =============================
    st.divider()
    st.subheader("📝 Qualitative Responses")

    for label, responses in qualitative_results.items():
        if responses:
            st.markdown(f"### {label}")
            st.dataframe(pd.DataFrame({label: responses}), use_container_width=True)

    # =============================
    # PDF REPORT
    # =============================
    st.set_page_config(page_title="SDO Masbate City Project DESA", layout="wide")
    st.title("SDO Masbate City Project DESA – Evaluation Dashboard")
    
    # ---- FORM 5 INPUTS ----
    st.subheader("Training Information (Form 5)")
    title = st.text_input("Title of Training Program")
    date_venue = st.text_input("Date and Venue")
    lsp_division = st.text_input("Learning Service Provider / Division")
    learning_areas = st.text_input("Learning Areas")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        teaching = st.number_input("No. of Teaching Participants", min_value=0)
    with c2:
        non_teaching = st.number_input("No. of Non‑Teaching Participants", min_value=0)
    with c3:
        teaching_related = st.number_input("No. of Teaching‑Related Participants", min_value=0)
    
    # ---- FILE UPLOAD ----
    uploaded_files = st.file_uploader(
        "Upload Daily and End-of-Program Evaluation Files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True
    )
    
    # ---- HELPERS ----
    def load_any_file(uploaded_file):
        try:
            return pd.read_excel(uploaded_file, engine="openpyxl")
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file)
    
    def detect_rating_columns(df):
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_keywords = ["id", "response"]
        return [c for c in numeric_cols if not any(k in c.lower() for k in exclude_keywords)]
    
    def get_file_overall_rating(df):
        rating_cols = detect_rating_columns(df)
        if not rating_cols:
            return None
        return round(df[rating_cols].mean().mean(), 2)
    
    # ---- PROCESS FILES ----
    daily_results = []
    end_program_result = None
    
    if uploaded_files:
        for f in uploaded_files:
            df = load_any_file(f)
            overall = get_file_overall_rating(df)
            fname = f.name.lower()
            if "daily_evaluation" in fname:
                daily_results.append((f.name, overall))
            elif "end_of_program" in fname:
                end_program_result = overall
    
    # ---- OVERALL FORMULA ----
    all_scores = [r for _, r in daily_results if r is not None]
    if end_program_result is not None:
        all_scores.append(end_program_result)
    
    overall_result = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    
    # ---- PDF GENERATION ----
    if st.button("Generate Form 5 PDF") and uploaded_files:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
    
        elements.append(Paragraph("<b>Overall Monitoring & Evaluation Results (Form 5)</b>", styles["Title"]))
    
        info_table = Table([
            ["Title of Training Program", title],
            ["Date and Venue", date_venue],
            ["Learning Service Provider / Division", lsp_division],
            ["Learning Areas", learning_areas],
            ["Teaching Participants", teaching],
            ["Non‑Teaching Participants", non_teaching],
            ["Teaching‑Related Participants", teaching_related],
        ])
    
        info_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke)
        ]))
    
        elements.append(info_table)
        elements.append(Paragraph("Result of Daily Online Evaluation", styles["Heading3"]))
    
        daily_table = [["File Name", "Overall Rating"]] + daily_results
        elements.append(Table(daily_table, style=[('GRID',(0,0),(-1,-1),1,colors.black)]))
    
        elements.append(Paragraph("Result of End-of-Program Evaluation", styles["Heading3"]))
        elements.append(Table([
            ["End‑of‑Program Evaluation", end_program_result]
        ], style=[('GRID',(0,0),(-1,-1),1,colors.black)]))
    
        elements.append(Paragraph(f"<b>Overall Result:</b> {overall_result}", styles["Heading2"]))
    
        doc.build(elements)
    
        with open(tmp.name, "rb") as f:
            st.download_button("Download Form 5 PDF", f, file_name="Form_5_Evaluation_Report.pdf")
    
    





from datetime import datetime

st.divider()

col_pic, col_text = st.columns([1, 6])

with col_pic:
    st.image("samson.png", width=80)

with col_text:
    st.markdown(
        f"""
        **Developed by Samson G. Capinig**  
        Senior Education Program Specialist, SMME  
        Project DESA • SDO Masbate City  
        © {datetime.now().year} . All rights reserved.
        """
    )


