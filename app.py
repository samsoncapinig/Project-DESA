
# app.py – Evaluation Dashboard v3 (Qualitative Summaries)

import streamlit as st
import pandas as pd
import numpy as np
import tempfile
import re
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Evaluation Dashboard v3", layout="wide")
st.title("📊 End of Program Evaluation Dashboard (v3)")
st.markdown("Includes quantitative analysis and summarized qualitative responses.")

# =============================
# CONSTANTS
# =============================
EXCLUDED_CATEGORIES = ["department", "group", "institution"]

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


def detect_qualitative_columns(df):
    mappings = {
        "Insights": ["insight"],
        "Most Significant Learning": ["most significant"],
        "Learnings": ["learning"],
        "Suggestions": ["suggestion"]
    }
    found = defaultdict(list)
    for col in df.columns:
        cl = col.lower()
        for label, keys in mappings.items():
            if any(k in cl for k in keys):
                found[label].append(col)
    return found


def clean_text(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.strip())


def summarize_responses(responses, max_sentences=3):
    sentences = []
    for r in responses:
        if isinstance(r, str):
            parts = re.split(r"[.!?]", r)
            for p in parts:
                p = clean_text(p)
                if 40 <= len(p) <= 200:
                    sentences.append(p)
    # deduplicate
    seen = set()
    unique = []
    for s in sentences:
        if s.lower() not in seen:
            unique.append(s)
            seen.add(s.lower())
    return unique[:max_sentences]

# =============================
# FILE UPLOADER
# =============================
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

all_tables = []
all_qualitative_text = defaultdict(list)

if uploaded_files:
    for f in uploaded_files:
        df = load_any_file(f)
        st.success(f"Loaded {f.name}")

        # -------- Quantitative --------
        rating_cols = detect_rating_columns(df)
        if rating_cols:
            overall = df[rating_cols].mean().mean()
            st.metric(f"Overall Rating – {f.name}", round(overall, 2))

            cat_df = pd.DataFrame({
                "Category": [extract_category(c) for c in rating_cols],
                "Average Rating": [df[c].mean() for c in rating_cols]
            })
            cat_df = cat_df[~cat_df["Category"].str.lower().isin(EXCLUDED_CATEGORIES)]
            cat_avg = cat_df.groupby("Category", as_index=False).mean()
            st.dataframe(cat_avg)
            st.bar_chart(cat_avg.set_index("Category"))
            all_tables.append(cat_avg)

        # -------- Qualitative Collection --------
        qual_map = detect_qualitative_columns(df)
        for label, cols in qual_map.items():
            for col in cols:
                all_qualitative_text[label].extend(df[col].dropna().astype(str).tolist())

    # =============================
    # CROSS FILE SUMMARY
    # =============================
    if all_tables:
        st.divider()
        combined = pd.concat(all_tables)
        combined = combined[~combined["Category"].str.lower().isin(EXCLUDED_CATEGORIES)]
        cross = combined.groupby("Category", as_index=False).mean()
        st.subheader("📊 Cross‑File Category Summary")
        st.dataframe(cross)

    # =============================
    # QUALITATIVE SUMMARIES
    # =============================
    st.divider()
    st.subheader("🧾 Qualitative Response Summaries")

    qualitative_summaries = {}

    for label, texts in all_qualitative_text.items():
        summaries = summarize_responses(texts)
        if summaries:
            qualitative_summaries[label] = summaries
            st.markdown(f"### {label}")
            for s in summaries:
                st.markdown(f"- {s}")

    # =============================
    # PDF REPORT
    # =============================
    if st.button("Generate PDF Report"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            doc = SimpleDocTemplate(tmp.name, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("Evaluation Summary Report", styles["Heading1"]))

            if all_tables:
                elements.append(Paragraph("Category Averages", styles["Heading2"]))
                table_data = [["Category", "Average Rating"]]
                for _, r in cross.iterrows():
                    table_data.append([r["Category"], round(r["Average Rating"], 2)])
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('BACKGROUND', (0,0), (-1,0), colors.grey)
                ]))
                elements.append(table)

            if qualitative_summaries:
                elements.append(Paragraph("Qualitative Summaries", styles["Heading2"]))
                for label, sums in qualitative_summaries.items():
                    elements.append(Paragraph(label, styles["Heading3"]))
                    for s in sums:
                        elements.append(Paragraph(f"- {s}", styles["Normal"]))

            doc.build(elements)

            with open(tmp.name, "rb") as f:
                st.download_button("Download PDF", f, "Evaluation_Report_v3.pdf")

else:
    st.info("Upload at least one file to begin.")
