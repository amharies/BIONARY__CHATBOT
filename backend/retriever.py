import os
import re
from dotenv import load_dotenv
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Optional
from database import engine

load_dotenv()

model = SentenceTransformer(
    "BAAI/bge-base-en-v1.5",
    trust_remote_code=True
)

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'(.)\1+', r'\1', text)
    return text

def hybrid_query(
    user_query: str,
    date_filter: Optional[str] = None,
    fee_filter: Optional[int] = None,
    vector_weight: float = 0.4,
    trigram_weight: float = 0.6,
    vector_threshold: float = 0.7,
    limit: Optional[int] = 5,
    fuzzy_query: Optional[str] = None,
):
    try:
        user_query = normalize_text(user_query)
        fuzzy_query = normalize_text(fuzzy_query) if fuzzy_query else user_query

        embedding = model.encode(user_query)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        user_vector_str = "[" + ",".join(map(str, embedding)) + "]"

        with engine.connect() as conn:
            conn.execute(text("SET pg_trgm.similarity_threshold = 0.15;"))

            sql_where_clauses = []
            sql_params = {
                "user_query": fuzzy_query,
                "user_vector": user_vector_str,
                "vector_weight": vector_weight,
                "trigram_weight": trigram_weight,
                "vector_threshold": vector_threshold,
            }

            if date_filter:
                if "BETWEEN" in date_filter:
                    sql_where_clauses.append(date_filter)
                else:
                    sql_where_clauses.append(f"date_of_event > '{date_filter}'")

            if fee_filter is not None:
                if fee_filter == 0:
                    sql_where_clauses.append("registration_fee = 0")
                else:
                    sql_where_clauses.append(f"registration_fee <= {fee_filter}")

            search_clause = """
            (
                word_similarity(:user_query, LOWER(search_text)) > 0.3
                OR LOWER(search_text) ILIKE '%' || :user_query || '%'
                OR embedding <=> :user_vector < :vector_threshold
            )
            """

            sql_where_clauses.append(search_clause)

            where_clause = "WHERE " + " AND ".join(sql_where_clauses)
            limit_clause = f"LIMIT {limit}" if limit else ""

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
                    (
                        (1 - (embedding <=> :user_vector)) * :vector_weight
                        + word_similarity(:user_query, LOWER(search_text)) * :trigram_weight
                    ) AS final_score
                FROM events
                {where_clause}
                ORDER BY final_score DESC
                {limit_clause};
            """

            print(sql_query)

            result = conn.execute(text(sql_query), sql_params)
            rows = result.mappings().fetchall()

        return [dict(row) for row in rows] if rows else []

    except Exception as e:
        print("Hybrid query error:", e)
        return []

def get_event_by_name(event_name: str):
    try:
        event_name = normalize_text(event_name)
        with engine.connect() as conn:
            print("SELECT * FROM events WHERE normalize(name_of_event) = :event_name")
            result = conn.execute(
                text(
                    "SELECT * FROM events WHERE normalize(name_of_event) = :event_name"
                ),
                {"event_name": event_name},
            )
            row = result.mappings().first()
        return dict(row) if row else None
    except Exception as e:
        print("Get event by name error:", e)
        return None

def add_new_event(form_data: dict):
    try:
        search_text = normalize_text(
            f"{form_data.get('name_of_event', '')} "
            f"{form_data.get('event_domain', '')} "
            f"{form_data.get('description_insights', '')} "
            f"{form_data.get('perks', '')} "
            f"{form_data.get('speakers', '')} "
            f"{form_data.get('faculty_coordinators', '')} "
            f"{form_data.get('student_coordinators', '')}"
        )

        embedding = model.encode(search_text)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        with engine.begin() as conn:
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
        print("Insert error:", e)
        return {"status": "error", "message": str(e)}
