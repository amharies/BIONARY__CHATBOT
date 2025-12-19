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

def extract_search_terms(text: str) -> str:
    """
    Uses Gemini to extract the core search subject/entity from natural language.
    Example: "what events did jeffry do" -> "Jeffry"
    """
    try:
        prompt = f"""
        Extract the main entity, person, or topic from this query for a database search.
        Remove words like "events", "about", "did", "done", "show", etc.
        Return ONLY the raw search term.
        
        Query: "{text}"
        Search Term:
        """
        response = llm.generate_content(prompt)
        cleaned = response.text.strip().replace('"', '')
        return cleaned
    except Exception:
        # Fallback to simple cleaning if LLM fails
        return re.sub(r"[^a-z0-9\s]", "", text.lower())

def gemini_answer(question, context):
    prompt = f"""
    You are a university knowledge assistant that generates professional, clean, and readable event reports.

    Answer the user’s question using only the information provided in the context.
    If information is insufficient or missing, state that clearly and gracefully.

    **Tone and behavior:**
    - Use a concise, professional, and friendly tone.
    - Avoid unnecessary explanations or filler.
    - Sound like a reliable university portal, not a casual chatbot.

    **Formatting rules (strict):**
    - **Do NOT use markdown headers.**
    - **Do NOT use bullet points.**
    - Do not use decorative symbols or separators for visual design.
    - Use **bold text** only when absolutely necessary, primarily for event titles.
    - Do not overuse emphasis.

    **Event layout principles:**
    - Structure responses for fast scanning and clarity.
    - Prefer structured formats over paragraphs when listing multiple events.

    **Allowed presentation styles:**
    - **Table format is preferred** when listing multiple events.
    - Use clear column labels such as Event Name, Date, Time, Mode, Venue, Registration Fee, Description.
    - If descriptions are long, use one table per event with two columns: **Label | Value**

    - **Card-style text blocks are allowed:**
        - Event title on its own line (**bold**).
        - Followed by consistently ordered fields: Date, Time, Mode, Venue, Registration Fee.
        - End with a short description paragraph (maximum two lines).
        - Separate events using whitespace only.

    **Summary usage:**
    - When multiple events are listed, include a brief summary at the top (Total events, Date range, Modes).

    **Data handling:**
    - Never expose raw values like NaN or null. Replace with "Not specified", "To be announced", etc.
    - Always keep the same field order across all events.
    - Alignment and consistency matter more than decoration.

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

    fuzzy_query = extract_search_terms(q)

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
