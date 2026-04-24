
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
    if st.button("Generate PDF Report"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            doc = SimpleDocTemplate(tmp.name, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("SDO Masbate City – Evaluation Report", styles["Heading1"]))
            elements.append(Paragraph("Combined Category Ratings", styles["Heading2"]))

            table_data = [["Category"] + list(combined_df.columns)]
            for idx, row in combined_df.iterrows():
                table_data.append([idx] + [round(v, 2) for v in row.values])

            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)
            ]))
            elements.append(table)

            elements.append(Paragraph("Qualitative Responses", styles["Heading2"]))
            for label, responses in qualitative_results.items():
                elements.append(Paragraph(label, styles["Heading3"]))
                for r in responses:
                    elements.append(Paragraph(r, styles["Normal"]))

            doc.build(elements)
            with open(tmp.name, "rb") as f:
                st.download_button("Download PDF", f, "Evaluation_Report_v6.pdf")
else:
    st.info("Upload at least one evaluation file to begin.")















st.divider()

col_pic, col_text = st.columns([1, 6])

with col_pic:
    st.image("samson.png", width=80)

with col_text:
    st.markdown(
        """
        **Developed by Samson Capinig**  
        Project DESA • SDO Masbate City  
        Built for everyone's benefits
        """
    )

