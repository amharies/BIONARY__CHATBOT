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

    # =====================================================
    # EVENTS COUNT
    # =====================================================
    if "how many" in q and "event" in q:
        sql = "SELECT COUNT(*) FROM events"
        if year:
            sql += f" WHERE EXTRACT(YEAR FROM date_of_event) = {year}"

        rows = retriever_module.query_relational_db(sql)
        count = rows[0][0] if rows else 0

        return gemini_answer(
            question,
            f"Total events found: {count}"
        )

    # =====================================================
    # FULL REPORT (FIXED: NO LIMIT)
    # =====================================================
    if "report" in q or "summary" in q:
        sql = """
        SELECT
            name_of_event, event_domain, date_of_event, time_of_event,
            venue, mode_of_event, registration_fee, speakers, perks,
            description_insights, faculty_coordinators, student_coordinators,
            collaboration
        FROM events
        """
        if year:
            sql += f" WHERE EXTRACT(YEAR FROM date_of_event) = {year}"
        sql += " ORDER BY date_of_event"

        rows = retriever_module.query_relational_db(sql)

        if not rows:
            return "No events found."

        context = "\n".join(
            f"Event: {r[0]}\n"
            f"  Domain: {r[1]}\n"
            f"  Date: {r[2]}\n"
            f"  Time: {r[3]}\n"
            f"  Venue: {r[4]}\n"
            f"  Mode: {r[5]}\n"
            f"  Fee: {r[6]}\n"
            f"  Speakers: {r[7]}\n"
            f"  Perks: {r[8]}\n"
            f"  Description: {r[9]}\n"
            f"  Faculty Coordinators: {r[10]}\n"
            f"  Student Coordinators: {r[11]}\n"
            f"  Collaboration: {r[12]}"
            for r in rows
        )

        return gemini_answer(question, context)

    # =====================================================
    # MONTH AND YEAR QUERIES
    # =====================================================
    if month and year:
        sql = f"""
        SELECT
            name_of_event, event_domain, date_of_event, time_of_event,
            venue, mode_of_event, registration_fee, speakers, perks,
            description_insights, faculty_coordinators, student_coordinators,
            collaboration
        FROM events
        WHERE EXTRACT(MONTH FROM date_of_event) = {month}
          AND EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY date_of_event
        """
        rows = retriever_module.query_relational_db(sql)

        if not rows:
            return f"No events found in {datetime(year, month, 1).strftime('%B %Y')}."

        context = "\n".join(
            f"Event: {r[0]}\n"
            f"  Domain: {r[1]}\n"
            f"  Date: {r[2]}\n"
            f"  Time: {r[3]}\n"
            f"  Venue: {r[4]}\n"
            f"  Mode: {r[5]}\n"
            f"  Fee: {r[6]}\n"
            f"  Speakers: {r[7]}\n"
            f"  Perks: {r[8]}\n"
            f"  Description: {r[9]}\n"
            f"  Faculty Coordinators: {r[10]}\n"
            f"  Student Coordinators: {r[11]}\n"
            f"  Collaboration: {r[12]}"
            for r in rows
        )
        return gemini_answer(question, context)
        
    # =====================================================
    # COORDINATOR / SPEAKER QUERIES
    # =====================================================
    if any(k in q for k in ["coordinate", "coordinator", "speaker", "who"]):
        person_name = extract_person_name(q)
        if person_name:
            sql = f"""
            SELECT
                name_of_event, event_domain, date_of_event, time_of_event,
                venue, mode_of_event, registration_fee, speakers, perks,
                description_insights, faculty_coordinators, student_coordinators,
                collaboration
            FROM events
            WHERE LOWER(student_coordinators) ILIKE '%{person_name.lower()}%'
               OR LOWER(faculty_coordinators) ILIKE '%{person_name.lower()}%'
               OR LOWER(speakers) ILIKE '%{person_name.lower()}%'
            """
            rows = retriever_module.query_relational_db(sql)

            if not rows:
                return "No events found for that person."

            context = "\n".join(
                f"Event: {r[0]}\n"
                f"  Domain: {r[1]}\n"
                f"  Date: {r[2]}\n"
                f"  Time: {r[3]}\n"
                f"  Venue: {r[4]}\n"
                f"  Mode: {r[5]}\n"
                f"  Fee: {r[6]}\n"
                f"  Speakers: {r[7]}\n"
                f"  Perks: {r[8]}\n"
                f"  Description: {r[9]}\n"
                f"  Faculty Coordinators: {r[10]}\n"
                f"  Student Coordinators: {r[11]}\n"
                f"  Collaboration: {r[12]}"
                for r in rows
            )
            return gemini_answer(question, context)

    # =====================================================
    # ONLINE / OFFLINE / HYBRID
    # =====================================================
    for mode in ["online", "offline", "hybrid"]:
        if mode in q:
            rows = retriever_module.query_relational_db(
                f"""
                SELECT
                    name_of_event, event_domain, date_of_event, time_of_event,
                    venue, mode_of_event, registration_fee, speakers, perks,
                    description_insights, faculty_coordinators, student_coordinators,
                    collaboration
                FROM events
                WHERE mode_of_event ILIKE '%{mode}%'
                ORDER BY date_of_event
                """
            )

            context = "\n".join(
                f"Event: {r[0]}\n"
                f"  Domain: {r[1]}\n"
                f"  Date: {r[2]}\n"
                f"  Time: {r[3]}\n"
                f"  Venue: {r[4]}\n"
                f"  Mode: {r[5]}\n"
                f"  Fee: {r[6]}\n"
                f"  Speakers: {r[7]}\n"
                f"  Perks: {r[8]}\n"
                f"  Description: {r[9]}\n"
                f"  Faculty Coordinators: {r[10]}\n"
                f"  Student Coordinators: {r[11]}\n"
                f"  Collaboration: {r[12]}"
                for r in rows
            )
            return gemini_answer(question, context)

    # =====================================================
    # DOMAIN / DEPARTMENT QUERIES
    # =====================================================
    domains = ["ai", "ml", "robotics", "web", "cloud", "blockchain", "iot", "cyber"]
    for d in domains:
        if d in q:
            rows = retriever_module.query_relational_db(
                f"""
                SELECT
                    name_of_event, event_domain, date_of_event, time_of_event,
                    venue, mode_of_event, registration_fee, speakers, perks,
                    description_insights, faculty_coordinators, student_coordinators,
                    collaboration
                FROM events
                WHERE event_domain ILIKE '%{d}%'
                """
            )
            context = "\n".join(
                f"Event: {r[0]}\n"
                f"  Domain: {r[1]}\n"
                f"  Date: {r[2]}\n"
                f"  Time: {r[3]}\n"
                f"  Venue: {r[4]}\n"
                f"  Mode: {r[5]}\n"
                f"  Fee: {r[6]}\n"
                f"  Speakers: {r[7]}\n"
                f"  Perks: {r[8]}\n"
                f"  Description: {r[9]}\n"
                f"  Faculty Coordinators: {r[10]}\n"
                f"  Student Coordinators: {r[11]}\n"
                f"  Collaboration: {r[12]}"
                for r in rows
            )
            return gemini_answer(question, context)

    # =====================================================
    # RAG / SEMANTIC QUESTIONS (FALLBACK)
    # =====================================================
    vector_results = retriever_module.query_vector_db(question)

    if vector_results:
        context = "\n\n".join(vector_results)
        return gemini_answer(question, context)

    return "I do not have enough information to answer that."
