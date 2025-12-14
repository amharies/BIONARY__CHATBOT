import os
from dotenv import load_dotenv
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
import numpy as np

from typing import Optional

from database import engine

load_dotenv()

# ────────────────────────────────────────────────
# EMBEDDING MODEL
# ────────────────────────────────────────────────
model = SentenceTransformer(
    "BAAI/bge-base-en-v1.5",
    trust_remote_code=True
)

# ────────────────────────────────────────────────
# HYBRID QUERY
# ────────────────────────────────────────────────
def hybrid_query(
    user_query: str,
    date_filter: Optional[str] = None,
    fee_filter: Optional[int] = None,
    vector_weight: float = 0.7,
    trigram_weight: float = 0.3,
    vector_threshold: float = 0.7,
):
    """
    Performs a hybrid search on the events table using a combination of
    hard filters, vector search, and trigram fuzzy search.
    """
    try:
        # 1. Get embedding for the user query
        embedding = model.encode(user_query)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        # Convert the list to a string representation of a vector
        user_vector_str = "[" + ",".join(map(str, embedding)) + "]"

        # 2. Construct and execute the hybrid SQL query
        with engine.connect() as conn:
            sql_where_clauses = []
            sql_params = {
                "user_query": user_query,
                "user_vector": user_vector_str,  # Pass the string representation
                "vector_weight": vector_weight,
                "trigram_weight": trigram_weight,
                "vector_threshold": vector_threshold,
            }

            if date_filter:
                if date_filter == "NOW()":
                    sql_where_clauses.append("date_of_event > NOW()")
                elif "BETWEEN" in date_filter:
                    sql_where_clauses.append(date_filter)
                else:
                    sql_where_clauses.append(f"date_of_event > '{date_filter}'")

            if fee_filter is not None:
                if fee_filter == 0:
                    sql_where_clauses.append("registration_fee = 0")
                else:
                    sql_where_clauses.append(f"registration_fee <= {fee_filter}")

            # Always include fuzzy and vector search
            search_clauses = [
                "search_text % :user_query",
                "embedding <=> :user_vector < :vector_threshold",
            ]
            sql_where_clauses.append(f"({' OR '.join(search_clauses)})")

            where_clause = "WHERE " + " AND ".join(sql_where_clauses) if sql_where_clauses else ""

            # Always calculate final_score
            sql_query = f"""
                SELECT
                    name_of_event,
                    event_domain,
                    date_of_event,
                    time_of_event,
                    venue,
                    mode_of_event,
                    registration_fee,
                    speakers,
                    faculty_coordinators,
                    student_coordinators,
                    perks,
                    collaboration,
                    description_insights,
                    ( (1 - (embedding <=> :user_vector)) * :vector_weight ) + ( similarity(search_text, :user_query) * :trigram_weight ) as final_score
                FROM events
                {where_clause}
                ORDER BY final_score DESC
                LIMIT 5;
                """
            
            print("─" * 80)
            print("HYBRID SEARCH (VECTOR + TRIGRAM)")
            print(sql_query)
            print("─" * 80)

            sql = text(sql_query)
            result = conn.execute(sql, sql_params)
            rows = result.mappings().fetchall()  # Use mappings to get dicts

        if not rows:
            return []

        # Convert rows to a list of dictionaries
        return [dict(row) for row in rows]

    except Exception as e:
        print("❌ Hybrid query error:", e)
        return []

def query_fuzzy_event_name(text_query: str):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        name_of_event,
                        event_domain,
                        date_of_event,
                        time_of_event,
                        venue,
                        description_insights,
                        similarity(name_of_event, :q) AS score
                    FROM events
                    ORDER BY score DESC
                    LIMIT 3
                """),
                {"q": text_query},
            )
            rows = result.fetchall()

        return [
            f"{r[0]}\n"
            f"Domain: {r[1]}\n"
            f"Date: {r[2]}\n"
            f"Time: {r[3]}\n"
            f"Venue: {r[4]}\n"
            f"Details: {r[5]}"
            for r in rows
        ] if rows else []

    except Exception:
        return []

# ────────────────────────────────────────────────
# INSERT NEW EVENT (THIS WAS MISSING 🚨)
# ────────────────────────────────────────────────
def add_new_event(form_data: dict):
    try:
        search_text = (
            f"{form_data.get('name_of_event', '')} "
            f"{form_data.get('event_domain', '')} "
            f"{form_data.get('description_insights', '')} "
            f"{form_data.get('perks', '')}"
        )

        embedding = model.encode(search_text)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        with engine.begin() as conn:  # ✅ auto-commit
            conn.execute(
                text(
                    """
                    INSERT INTO events (
                        name_of_event,
                        event_domain,
                        date_of_event,
                        time_of_event,
                        faculty_coordinators,
                        student_coordinators,
                        venue,
                        mode_of_event,
                        registration_fee,
                        speakers,
                        perks,
                        collaboration,
                        description_insights,
                        search_text,
                        embedding
                    )
                    VALUES (
                        :name_of_event,
                        :event_domain,
                        :date_of_event,
                        :time_of_event,
                        :faculty_coordinators,
                        :student_coordinators,
                        :venue,
                        :mode_of_event,
                        :registration_fee,
                        :speakers,
                        :perks,
                        :collaboration,
                        :description_insights,
                        :search_text,
                        :embedding
                    )
                    """
                ),
                {
                    **form_data,
                    "search_text": search_text,
                    "embedding": embedding,
                },
            )

        return {"status": "success"}

    except Exception as e:
        print("❌ Insert error:", e)
        return {"status": "error", "message": str(e)}
