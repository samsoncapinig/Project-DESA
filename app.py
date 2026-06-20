# =============================
# IMPORTS
# =============================
import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import random
from collections import defaultdict
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from report_generator import generate_report
from ppt_generator import generate_ppt_report
import tempfile
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
        "Develop also findings, analysis and recommendations. "
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
    1. A short findings from responses of about 100 words
    2. A short analysis of responses of about 100 words
    3. Recommendations of about 100 words

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
    sample_size = min(len(responses), 80)  # max 80, or less if not enough data
    sampled_responses = random.sample(responses, sample_size)

    combined_text = "\n---\n".join(sampled_responses)
    prompt = f"""
    Based on the following participant responses:

    {combined_text}

    1. Make a short finding of these responses.
       
    2. Make a short analysis of these responses.
       Include strengths and weaknesses.

    3. Make a short summary of recommendations based from the responses.

    Format:

    FINDINGS:
    ...
    
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
participant_summary = [

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
        # PARTICIPANT TYPE COUNT
        # =============================
  
        teaching = 0
        non_teaching = 0
        teaching_related = 0

        participant_col = None

        # ✅ Step 3.1: Find the correct column automatically
        for col in df.columns:
            if "description" in col.lower():
                participant_col = col
                    break

# ✅ Step 3.2: Count participants
        if participant_col:
            series = df[participant_col].dropna().astype(str)
        
            # ✅ Correct logic (NO double counting)
            teaching_related = series.str.contains("Teaching Related", case=False).sum()
            non_teaching = series.str.contains("Non-Teaching", case=False).sum()
        
            teaching = (
                series.str.contains(r"\bTeaching\b", case=False, regex=True).sum()
                - teaching_related
            )
        
        # ✅ Step 3.3: Total respondents
        total_participants = len(df)
        
        # ✅ Step 3.4: Save to list
        participant_summary.append({
            "File Name": f.name,
            "Teaching": teaching,
            "Non-Teaching": non_teaching,
            "Teaching Related": teaching_related,
            "Total": total_participants
        })

# =============================
# PARTICIPANT TYPE SUMMARY TABLE
# =============================
if participant_summary:
    st.subheader("👨‍🏫 Teaching vs Non-Teaching Summary")

    participant_df = pd.DataFrame(participant_summary)

    # ✅ Compute totals
    totals = participant_df[["Teaching", "Non-Teaching", "Teaching Related", "Total"]].sum()

    # ✅ Add TOTAL row
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
# COMBINED QUALITATIVE DATA
# =============================
all_qualitative_responses = []

for responses in qualitative_results.values():
    all_qualitative_responses.extend(responses)

# =============================
# COMBINED QUALITATIVE TABLE + AI BUTTON
# =============================

if all_qualitative_responses:
    st.subheader("📋 Combined Qualitative Responses")

    combined_df = pd.DataFrame({
        "Participant Responses": all_qualitative_responses
    })

    st.dataframe(combined_df, use_container_width=True)

    # ✅ AI Analysis Button
    if st.button("Analyze All Qualitative Responses"):
        with st.spinner("Analyzing all responses..."):
            ai_result = generate_qualitative_analysis(all_qualitative_responses)

        st.markdown("## 🤖 Overall Analysis & Recommendations")
        st.write(ai_result)

        # ✅ SPLIT OUTPUT
        combined_analysis = ""
        combined_recommendation = ""

        if "RECOMMENDATIONS:" in ai_result:
            parts = ai_result.split("RECOMMENDATIONS:")
            combined_analysis = parts[0].replace("ANALYSIS:", "").strip()
            combined_recommendation = parts[1].strip()
        else:
            combined_analysis = ai_result

        # ✅ SAVE FOR REPORT USE
        st.session_state["analysis"] = combined_analysis
        st.session_state["recommendation"] = combined_recommendation

                
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
# REPORT GENERATOR UI (SHOW ONLY IF FILES EXIST)
# =============================
if uploaded_files:

    st.subheader("📊 Generate Reports")

    # Create two tabs: one for Word, one for PowerPoint
    tab_word, tab_ppt = st.tabs(["📄 Generate Form 5 (Word)", "📊 Generate PowerPoint"])

    with tab_word:
        st.markdown("### Form 5 - MS Word Report")
        
        training_title = st.text_input("Title of Training Program", key="word_title")
        date = st.text_input("Date and Venue", key="word_date")
        learning_service_provider = st.text_input("Learning Service Provider/Division", key="word_provider")
        learning_areas = st.text_input("Learning Areas", key="word_areas")

        number_of_teaching_participants = st.number_input(
            "Number of Teaching Participants", min_value=0, step=1, key="word_teaching"
        )

        number_of_non_teaching_participants = st.number_input(
            "Number of Non-Teaching Participants", min_value=0, step=1, key="word_non_teaching"
        )

        number_of_teaching_related_participants = st.number_input(
            "Number of Teaching Related Participants", min_value=0, step=1, key="word_teaching_related"
        )

        # ✅ GENERATE AI NARRATIVE
        if st.button("Generate Form 5"):
            # ✅ If no AI analysis yet, generate automatically
            if "analysis" not in st.session_state or not st.session_state["analysis"]:
                if all_qualitative_responses:
                    with st.spinner("Generating AI analysis for report..."):
                        ai_result = generate_qualitative_analysis(all_qualitative_responses)

                    # ✅ Split result
                    if "RECOMMENDATIONS:" in ai_result:
                        parts = ai_result.split("RECOMMENDATIONS:")
                        st.session_state["analysis"] = parts[0].replace("ANALYSIS:", "").strip()
                        st.session_state["recommendation"] = parts[1].strip()
                    else:
                        st.session_state["analysis"] = ai_result
                        st.session_state["recommendation"] = ""
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

            # ✅ GENERATE REPORT
            st.markdown("### Generate Report")
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
                    "📥 Download Form 5 (Word)",
                    file,
                    file_name=filepath
                )

    with tab_ppt:
        st.markdown("### PowerPoint Report")
        
        ppt_training_title = st.text_input("Title of Training Program", key="ppt_title")
        ppt_date = st.text_input("Date Conducted", key="ppt_date")
        ppt_venue = st.text_input("Venue", key="ppt_venue")
        ppt_program_owner = st.text_input("Program Owner", key="ppt_owner")

        if st.button("Generate PowerPoint Report"):
            if all([ppt_training_title, ppt_date, ppt_venue, ppt_program_owner]):
                with st.spinner("Generating PowerPoint report..."):
                    # Prepare daily rating data (combine all files)
                    daily_rating_dict = {}
                    for file_name, ratings in daily_results.items():
                        for category, value in ratings.items():
                            daily_rating_dict[category] = value
                    
                    # Prepare end-of-program rating data (combine all files)
                    end_rating_dict = {}
                    for file_name, ratings in end_program_results.items():
                        for category, value in ratings.items():
                            end_rating_dict[category] = value
                    
                    # Prepare data for PPT
                    ppt_data = {
                        "training_title": ppt_training_title,
                        "date": ppt_date,
                        "venue": ppt_venue,
                        "program_owner": ppt_program_owner,
                        "daily_general_average": round(overall_daily, 2) if 'overall_daily' in locals() else 0,
                        "end_of_program_average": round(overall_end, 2) if 'overall_end' in locals() else 0,
                        "overall_results": round(final_rating, 2) if 'final_rating' in locals() else 0,
                        "analysis": st.session_state.get("analysis", ""),
                        "recommendation": st.session_state.get("recommendation", "")
                    }
                    
                    # Debug: Show what data we're passing
                    st.info(f"📋 Daily categories detected: {list(daily_rating_dict.keys())}")
                    st.info(f"📋 End-of-program categories detected: {list(end_rating_dict.keys())}")
                    
                    ppt_filepath = generate_ppt_report(ppt_data, daily_rating_dict, end_rating_dict)
                
                st.success("✅ PowerPoint Report Generated!")
                
                with open(ppt_filepath, "rb") as file:
                    st.download_button(
                        "📥 Download PowerPoint Report",
                        file,
                        file_name=ppt_filepath
                    )
            else:
                st.error("Please fill in all required fields for the PowerPoint report.")

# =============================
# QUALITATIVE RESPONSES - AUTO ANALYSIS (FIXED)
# =============================
has_daily = len(daily_results) > 0
has_end = len(end_program_results) > 0

# ✅ CASE 1: BOTH Daily + End → AUTOMATIC AI MODE (ONLY ONCE)
if has_daily and has_end:
    # ✅ Check if auto-analysis has already been generated
    if "auto_analysis_generated" not in st.session_state:
        if all_qualitative_responses:
            with st.spinner("Generating AI Analysis..."):
                ai_result = generate_qualitative_analysis(all_qualitative_responses)
            
            st.session_state["auto_analysis_generated"] = True
            st.session_state["auto_ai_result"] = ai_result
    
    # ✅ Display the cached result (without regenerating)
    if st.session_state.get("auto_analysis_generated"):
        st.divider()
        st.markdown("## 🤖 Analysis & Recommendations")
        st.write(st.session_state.get("auto_ai_result", ""))

        # ✅ SPLIT AI OUTPUT
        ai_result = st.session_state.get("auto_ai_result", "")
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
