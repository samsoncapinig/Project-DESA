
# app.py – Evaluation Dashboard v5 (STRICT Qualitative Header Detection)

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
st.set_page_config(page_title="SDO Masbate City Project DESA", layout="wide")
st.title("logo.png", width=80", "SDO Masbate City Project DESA")
st.markdown("Strict detection of qualitative column headers and full response listing.")

# =============================
# CONSTANTS
# =============================
EXCLUDED_CATEGORIES = ["department", "group", "institution"]

# STRICT REGEX PATTERNS FOR QUALITATIVE HEADERS
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
    """
    Detect qualitative columns ONLY if they strictly follow:
    Q<number><separator><expected label>
    """
    found = defaultdict(list)
    for col in df.columns:
        col_clean = col.strip()
        for label, pattern in QUAL_HEADER_PATTERNS.items():
            if re.match(pattern, col_clean, flags=re.IGNORECASE):
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

        # -------- STRICT QUALITATIVE LISTING --------
        qual_map = detect_strict_qualitative_columns(df)
        for label, cols in qual_map.items():
            for col in cols:
                responses = df[col].dropna().astype(str).tolist()
                all_qualitative_rows[label].extend(responses)

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
    st.subheader("📝 Full Qualitative Responses (Strict Detection)")

    if not all_qualitative_rows:
        st.warning("No qualitative columns matched the strict Q<number>_<Label> rule.")

    for label, responses in all_qualitative_rows.items():
        if responses:
            st.markdown(f"### {label}")
            st.caption(f"Detected using strict pattern: Q<number> + {label}")
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
                st.download_button("Download PDF", f, "Evaluation_Report_v5.pdf")

else:
    st.info("Upload at least one file to begin.")
