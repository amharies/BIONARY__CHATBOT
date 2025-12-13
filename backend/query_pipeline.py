import os
import re
from datetime import datetime
import google.generativeai as genai

import retriever as retriever_module
from dotenv import load_dotenv
load_dotenv()


# ────────────────────────────────────────────────
# GEMINI CONFIG
# ────────────────────────────────────────────────
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

CURRENT_YEAR = datetime.now().year

# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def extract_year(text):
    m = re.search(r"(19|20)\d{2}", text)
    return int(m.group()) if m else None


def extract_month(text):
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    for month_name, month_num in month_map.items():
        if month_name in text:
            return month_num
    return None

def extract_person_name(text):
    # This is a simple implementation and can be improved with more sophisticated NLP techniques
    keywords = ["who", "coordinate", "coordinator", "speaker", "events", "do"]
    
    # Sequentially remove keywords from the text
    for keyword in keywords:
        text = text.replace(keyword, "")
        
    # The remaining text should be the name
    return text.strip()

def gemini_answer(question, context):
    """
    Gemini ADDS language, NOT facts.
    """
    prompt = f"""
You are a university knowledge assistant.

You must answer the question ONLY using the information below.
If information is missing, say so clearly.

Question:
{question}

Information:
{context}

Answer clearly, professionally, and naturally.
"""
    response = llm.generate_content(prompt)
    return response.text.strip()


# ────────────────────────────────────────────────
# MAIN AGENT
# ────────────────────────────────────────────────
def handle_user_query(question: str) -> str:
    q = question.lower()
    year = extract_year(q)
    month = extract_month(q)

    # Default filters
    date_filter = "NOW()"
    fee_filter = 5000  # Default to a high value

    # More specific date filters if month and year are extracted
    if year and month:
        # Create a date range for the specified month and year
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31" # Simplification, but works for filtering
        date_filter = f"date_of_event BETWEEN '{start_date}' AND '{end_date}'"
    elif year:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        date_filter = f"date_of_event BETWEEN '{start_date}' AND '{end_date}'"


    # Fee filter
    if "free" in q:
        fee_filter = 0

    # Extract person name for coordinator/speaker queries
    person_name = None
    if any(k in q for k in ["coordinate", "coordinator", "speaker", "who"]):
        person_name = extract_person_name(q)

    # Call the hybrid query
    print(f"DEBUG: date_filter passed to hybrid_query: {date_filter if date_filter != 'NOW()' else None}")
    print(f"DEBUG: fee_filter passed to hybrid_query: {fee_filter if fee_filter != 5000 else None}")
    results = retriever_module.hybrid_query(
        user_query=question,
        date_filter=date_filter if date_filter != "NOW()" else None,
        fee_filter=fee_filter if fee_filter != 5000 else None,
    )

    if not results:
        return "I do not have enough information to answer that."

    context = "\n\n".join(results)
    return gemini_answer(question, context)

