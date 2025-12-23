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
        return re.sub(r"[^a-z0-9\s]", "", text.lower())

def gemini_answer(question, context):
    prompt = f"""
    You are the University Event Portal Assistant. Your goal is to generate professional, high-clarity event reports.

    **Instructions:**
    1. Answer the user's question using ONLY the provided context.
    2. If the context is empty, politely state that no information is available.
    3. **Data Handling:** - If a fee is "0", display it as "Free".
       - If a value is "NaN", "None", or "TBA", display it as "Not specified".

    **Formatting Rules (Strict):**
    * **NO** Markdown headers (#, ##).
    * **NO** Bullet points (*, -).
    * **NO** Card-style layouts or text blocks.
    * **ALWAYS USE TABLES.**

    **Table Selection Logic:**
    * **Scenario A (List of Events):** Use a **Horizontal Table**.
      Columns: Event Name | Date | Time | Venue |
    
    * **Scenario B (Single Event or Detailed View):** Use a **Vertical Table**.
      Columns: **Attribute** | **Detail**
      (Rows should include: Event Name, Date, Time, Venue, Mode, Fee, Description, etc.)

    **Visual Examples:**

    ---
    *Example A: List View (Multiple Events)*
    Summary: Found 2 events.

    | Event Name | Date | Time | Venue |
    | :--- | :--- | :--- | :--- |
    | **Robotics 101** | 12 Oct 2024 | 10:00 AM | Lab 2 |
    | **AI Summit** | 15 Oct 2024 | 2:00 PM | Hall A |

    ---
    *Example B: Detail View (Single Event)*
    Summary: Details for "Deep Learning Workshop".

    | Attribute | Detail |
    | :--- | :--- |
    | **Event Name** | **Deep Learning Workshop** |
    | **Date** | 20 Nov 2024 |
    | **Time** | 9:00 AM |
    | **Venue** | Main Auditorium |
    | **Description** | A comprehensive workshop covering neural networks, backpropagation, and real-world applications of AI. |

    ---

    **Context:**
    {context}

    **User Question:**
    {question}

    **Answer:**
    """
    response = llm.generate_content(prompt)
    return response.text.strip()

def handle_user_query(question: str) -> dict:
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

    # Direct event lookup
    event_name = extract_event_name(q)
    # (Note: You can apply the cleaning logic here too if you wish, 
    # but the main cleaning happens in the loop below)

    fuzzy_query = extract_search_terms(q)

    query_data = retriever_module.hybrid_query(
        user_query=q,
        fuzzy_query=fuzzy_query,
        date_filter=date_filter,
        fee_filter=fee_filter,
        limit=None
    )

    results = query_data["results"]
    sql_query = query_data["sql_query"]

    if not results:
        return {"answer": "I do not have enough information to answer that.", "sql_query": sql_query}

    context_parts = []
    
    # Priority fields mapping (Matches the 'update_events_search_text' hierarchy)
    field_map = [
        ("event_domain", "Domain"),
        ("date_of_event", "Date"),
        ("time_of_event", "Time"),
        ("venue", "Venue"),
        ("mode_of_event", "Mode"),
        ("registration_fee", "Registration Fee"),
        ("speakers", "Speakers"),
        ("faculty_coordinators", "Faculty Coordinators"),
        ("student_coordinators", "Student Coordinators"),
        ("perks", "Perks"),
        ("collaboration", "Collaboration"),
        ("description_insights", "Description")
    ]

    for event in results:
        # Start with the event name
        details = [f"Event: {event.get('name_of_event', 'Unknown Event')}"]
        
        for key, label in field_map:
            val = event.get(key)
            val_str = str(val).strip()

            # --- TRIGRAM LOGIC (Data Cleaning) ---
            # 1. Skip if value is "NaN", "None", or empty
            if val is None or val_str.lower() in ['nan', 'none', '', 'null']:
                continue
            
            # 2. Handle Date Formatting
            if key == "date_of_event":
                try:
                    date_obj = datetime.strptime(val_str, '%Y-%m-%d')
                    val_str = date_obj.strftime('%d-%b-%Y')
                except ValueError:
                    # If parsing fails, keep original or handle as 'Not specified'
                    pass 

            # 3. Handle Zero Fee
            elif key == "registration_fee" and val_str == "0":
                val_str = "Free" 

            details.append(f"{label}: {val_str}")

        if "final_score" in event:
             details.append(f"Relevance Score: {event['final_score']:.2f}")

        context_parts.append(" | ".join(details))

    context = "\n\n".join(context_parts)
    answer = gemini_answer(question, context)
    return {"answer": answer, "sql_query": sql_query}
