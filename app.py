
# app.py
import streamlit as st
import pandas as pd
import numpy as np
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Evaluation Dashboard", layout="wide")
st.title("📊 End of Program Evaluation Dashboard")
st.markdown("Upload one or more evaluation CSV / Excel files to generate summaries.")

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

# =============================
# UPLOADER
# =============================
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

all_tables = []
all_qualitative = []

if uploaded_files:
    for f in uploaded_files:
        df = load_any_file(f)
        rating_cols = detect_rating_columns(df)
        if not rating_cols:
            continue

        overall = df[rating_cols].mean().mean()
        st.metric(f"Overall Rating – {f.name}", round(overall, 2))

        cat_df = pd.DataFrame({
            "Category": [extract_category(c) for c in rating_cols],
            "Average Rating": [df[c].mean() for c in rating_cols]
        })

        # FILTER UNWANTED CATEGORIES
        cat_df = cat_df[~cat_df["Category"].str.lower().isin(EXCLUDED_CATEGORIES)]

        cat_avg = cat_df.groupby("Category", as_index=False).mean()
        st.dataframe(cat_avg)
        st.bar_chart(cat_avg.set_index("Category"))
        all_tables.append(cat_avg)

        q_cols = [
            "Q12_Most Significant Learning",
            "Q13_Learnings",
            "Q14_Suggestions"
        ]
        q_cols = [c for c in q_cols if c in df.columns]
        if q_cols:
            qdf = df[q_cols].dropna(how="all")
            all_qualitative.append(qdf)

    # =============================
    # CROSS-FILE SUMMARY
    # =============================
    if all_tables:
        st.divider()
        combined = pd.concat(all_tables)
        combined = combined[~combined["Category"].str.lower().isin(EXCLUDED_CATEGORIES)]
        cross = combined.groupby("Category", as_index=False).mean()
        st.subheader("Cross‑File Category Summary")
        st.dataframe(cross)

    # =============================
    # QUALITATIVE FEEDBACK
    # =============================
    if all_qualitative:
        st.divider()
        st.subheader("Qualitative Feedback")
        st.dataframe(pd.concat(all_qualitative))

    # =============================
    # PDF REPORT
    # =============================
    if st.button("Generate PDF Report") and all_tables:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            doc = SimpleDocTemplate(tmp.name, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("Evaluation Report", styles["Heading1"]))
            table_data = [["Category", "Average Rating"]]

            for _, r in cross.iterrows():
                table_data.append([r["Category"], round(r["Average Rating"], 2)])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey)
            ]))

            elements.append(table)
            doc.build(elements)

            with open(tmp.name, "rb") as f:
                st.download_button("Download PDF", f, "Evaluation_Report.pdf")
else:
    st.info("Upload at least one file to begin.")
