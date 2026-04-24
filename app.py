
# app.py – Evaluation Dashboard v4 (Full Qualitative Listing)

import streamlit as st
import pandas as pd
import numpy as np
import tempfile
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Evaluation Dashboard v4", layout="wide")
st.title("📊 End of Program Evaluation Dashboard (v4)")
st.markdown("Displays full qualitative responses grouped by question type.")

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

# =============================
# FILE UPLOADER
# =============================
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

all_tables = []
all_qualitative_rows = defaultdict(list)

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

        # -------- Qualitative Listing --------
        qual_map = detect_qualitative_columns(df)
        for label, cols in qual_map.items():
            for col in cols:
                rows = df[[col]].dropna()
                for value in rows[col].astype(str).tolist():
                    all_qualitative_rows[label].append(value)

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
    # FULL QUALITATIVE RESPONSES
    # =============================
    st.divider()
    st.subheader("📝 Full Qualitative Responses")

    for label, responses in all_qualitative_rows.items():
        if responses:
            st.markdown(f"### {label}")
            df_out = pd.DataFrame({label: responses})
            st.dataframe(df_out, use_container_width=True)

    # =============================
    # PDF REPORT
    # =============================
    if st.button("Generate PDF Report"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            doc = SimpleDocTemplate(tmp.name, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("Evaluation Report", styles["Heading1"]))

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

            if all_qualitative_rows:
                elements.append(Paragraph("Qualitative Responses", styles["Heading2"]))
                for label, responses in all_qualitative_rows.items():
                    elements.append(Paragraph(label, styles["Heading3"]))
                    for r in responses:
                        elements.append(Paragraph(r, styles["Normal"]))

            doc.build(elements)

            with open(tmp.name, "rb") as f:
                st.download_button("Download PDF", f, "Evaluation_Report_v4.pdf")

else:
    st.info("Upload at least one file to begin.")
