import os
import re
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

import retriever as retriever_module

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

CURRENT_YEAR = datetime.now().year

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'(.)\1+', r'\1', text)
    return text

def extract_year(text):
    m = re.search(r"(19|20)\d{2}", text)
    return int(m.group()) if m else None

def extract_month(text):
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    for name, num in month_map.items():
        if name in text:
            return num
    return None

def extract_event_name(text):
    patterns = [
        r"of (.+)",
        r"for (.+)",
        r"about (.+)"
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None

def extract_keywords(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s]", "", text)
    stop_words = {
        "give","details","about","events","conducted","by","show","list",
        "me","tell","what","where","when","who","is","the","an","a","of",
        "in","on","at","for","to","from","with","all","every","some","any"
    }
    words = text.split()
    keywords = [w for w in words if w not in stop_words]
    return " ".join(keywords)

def gemini_answer(question, context):
    prompt = f"""
You are a helpful university knowledge assistant.

Answer the question ONLY using the information provided.
If information is insufficient, say so clearly.

Use markdown formatting.

Question:
{question}

Information:
{context}

Answer:
"""
    response = llm.generate_content(prompt)
    return response.text.strip()

def handle_user_query(question: str) -> str:
    q = normalize_text(question)

    year = extract_year(q)
    month = extract_month(q)

    date_filter = None
    fee_filter = None

    if year and month:
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
        date_filter = f"date_of_event BETWEEN '{start_date}' AND '{end_date}'"
    elif year:
        date_filter = f"date_of_event BETWEEN '{year}-01-01' AND '{year}-12-31'"

    if "free" in q:
        fee_filter = 0

    event_name = extract_event_name(q)
    if event_name:
        event = retriever_module.get_event_by_name(normalize_text(event_name))
        if event:
            details = [f"## {event.get('name_of_event','N/A')}"]
            for k, label in [
                ("date_of_event","Date"),
                ("time_of_event","Time"),
                ("venue","Venue"),
                ("mode_of_event","Mode"),
                ("registration_fee","Registration Fee"),
                ("speakers","Speakers"),
                ("faculty_coordinators","Faculty Coordinators"),
                ("student_coordinators","Student Coordinators"),
                ("perks","Perks"),
                ("collaboration","Collaboration"),
                ("description_insights","Description")
            ]:
                if event.get(k) is not None:
                    details.append(f"**{label}:** {event[k]}")
            return gemini_answer(question, "\n".join(details))

    fuzzy_query = extract_keywords(q)

    results = retriever_module.hybrid_query(
        user_query=q,
        fuzzy_query=fuzzy_query,
        date_filter=date_filter,
        fee_filter=fee_filter,
        limit=None
    )

    if not results:
        return "I do not have enough information to answer that."

    context_parts = []
    for event in results:
        details = [f"## {event.get('name_of_event','N/A')}"]
        for k, label in [
            ("date_of_event","Date"),
            ("time_of_event","Time"),
            ("venue","Venue"),
            ("mode_of_event","Mode"),
            ("registration_fee","Registration Fee"),
            ("speakers","Speakers"),
            ("faculty_coordinators","Faculty Coordinators"),
            ("student_coordinators","Student Coordinators"),
            ("perks","Perks"),
            ("collaboration","Collaboration"),
            ("description_insights","Description")
        ]:
            if event.get(k) is not None:
                details.append(f"**{label}:** {event[k]}")
        if "final_score" in event:
            details.append(f"**Relevance Score:** {event['final_score']:.2f}")
        context_parts.append("\n".join(details))

    context = "\n\n---\n\n".join(context_parts)
    return gemini_answer(question, context)
