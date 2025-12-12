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
    # RAG / SEMANTIC QUESTIONS
    # =====================================================
    vector_results = retriever_module.query_vector_db(question)

    if vector_results:
        context = "\n\n".join(vector_results)
        return gemini_answer(question, context)

    return "I do not have enough information to answer that."
