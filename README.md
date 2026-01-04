# Bionary Fullstack Agent

## Overview

This project is a full-stack "Retrieval-Augmented Generation" (RAG) application designed to answer user questions about university club events. It features a React/Next.js frontend and a Python/FastAPI backend that leverages a PostgreSQL database with vector support and the Google Gemini language model.

## Project Structure

The project is divided into two main parts:

- `frontend/`: A [Next.js](https://nextjs.org/) application that provides the user interface.
- `backend/`: A [FastAPI](https://fastapi.tiangolo.com/) application that handles the core logic.

---
## Architecture Diagram

```mermaid
---
config:
  layout: dagre
  look: classic
---
flowchart TB
    User(("User<br>Web Interface")) -- submits credentials --> Backend["Backend API (FastAPI)<br>Authentication, Event Management"]
    User -- sends chat query --> Backend
    Admin(("Admin<br>Event Management")) -- submits event data --> Backend
    Backend -- issues JWT token --> User
    Backend -- validates token --> User
    Backend -- stores event data --> DB[("Neon Database<br><br>")]
    Backend -- generates embeddings --> DB
    Backend -- normalizes query --> AI["AI &amp; Retrieval Pipeline<br>Gemini, SentenceTransformers"]
    AI -- retrieves relevant events --> DB
    AI -- sends prompt to Gemini --> AI
    AI -- returns response --> Backend
    Backend -- sends response back --> User
    DB -- stores user data --> Backend
    DB -- stores event details --> Backend
    DB -- stores logs --> Backend
    Backend -- interacts with neon database --> DB
    Backend -- calls Gemini API --> AI
    AI -- uses SentenceTransformers --> AI
    Backend -- handles user sessions --> User
    Backend -- processes event management --> Admin
    Frontend["Frontend (Next.js)<br>User Interface, Chat, Event Management"]

     Backend:::core
     DB:::db
     AI:::core
     Frontend:::core
    classDef core fill:#1E90FF,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px
    classDef db fill:#9ACD32,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px
    classDef external fill:#FFD700,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px
```
---

## Backend

The backend is a FastAPI application that provides a chat API and an API for adding events.

### Features

- **Chat API (`/api/chat`):** This endpoint uses a RAG pipeline to answer questions about university events. It takes a natural language query, performs a hybrid search (semantic vector search + trigram fuzzy search) on a PostgreSQL database, and uses the Google Gemini language model to generate a natural, well-formatted answer.
- **Add Event API (`/api/add-event`):** This is a protected endpoint for adding new events to the database. It generates and stores vector embeddings for the event data to enable semantic search.
- **Authentication:** Authentication for protected endpoints is handled using JSON Web Tokens (JWT).
- **Request Logging:** Every query to `/api/chat`, its corresponding generated answer, and the raw SQL query used for retrieval is recorded in a `logs` table with an IST timestamp for monitoring and analysis.

### Technologies

- **FastAPI:** A modern, fast web framework for building APIs with Python.
- **PostgreSQL with `pgvector` and `pg_trgm`:** A powerful, open-source object-relational database used for storing event data, vector embeddings (`pgvector`), and enabling efficient fuzzy text search (`pg_trgm`).
- **Sentence-Transformers:** A Python library for generating high-quality sentence and text embeddings.
- **Google Gemini:** A family of large language models from Google AI used for generating the final answer.

---

## Frontend

The frontend is a Next.js application built with React that provides a clean and intuitive chat interface for users to interact with the agent.

### Features
- **Chat Interface:** A simple, modern interface for sending queries to the backend and displaying the agent's response.
- **Loading State:** Provides visual feedback to the user while the agent is processing a query.
- **Admin Link:** A link to a separate admin dashboard for managing events.

### Technologies

- **Next.js:** A React framework for building server-side rendered and static web applications.
- **React:** A JavaScript library for building user interfaces.
- **axios:** A promise-based HTTP client for making requests to the backend API.
- **Tailwind CSS:** A utility-first CSS framework for rapidly building custom designs.

---

## Getting Started

### Prerequisites

*   Node.js and npm (for the frontend)
*   Python 3.7+ and pip (for the backend)
*   PostgreSQL (with the `pgvector` and `pg_trgm` extensions enabled)

### Environment Variables (.env)

Create a `.env` file in the `backend/` directory with the following content:

```
DATABASE_URL="postgresql://user:password@host:port/database_name"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
SECRET_KEY="YOUR_SECRET_KEY_FOR_JWT"
```

*   **`DATABASE_URL`**: Connection string for your PostgreSQL database.
*   **`GEMINI_API_KEY`**: Your API key for accessing the Google Gemini language model.
*   **`SECRET_KEY`**: A strong, random secret key used for signing JWT tokens. You can generate one using `openssl rand -hex 32`.

### Database Setup

1.  **Install Extensions:**
    Connect to your PostgreSQL database and run the following commands to enable the necessary extensions:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    ```

2.  **Create Tables:**
    - The `users` and `logs` tables are created automatically by the application on startup (thanks to SQLAlchemy).
    - The `logs` table has the following columns: `id`, `date`, `time`, `question`, `answer`, and `sql_query` (type `TEXT`).
    - You will need to create the `events` table. The schema is defined by the columns in `data/events_table_schema.txt`.

3.  **Create the Search Trigger Function:**
    This function automatically concatenates relevant fields into the `search_text` column, which is used for trigram-based fuzzy search.
    ```sql
    CREATE OR REPLACE FUNCTION update_events_search_text()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.search_text := concat_ws(' ', 
            -- Use NULLIF to turn "NaN" text into real NULLs so they get skipped
            NULLIF(NEW.name_of_event::text, 'NaN'),
            NULLIF(NEW.event_domain::text, 'NaN'),
            
            -- Date doesn't have "NaN", so just text is fine
            NEW.date_of_event::text,
            
            NULLIF(NEW.time_of_event::text, 'NaN'),
            NULLIF(NEW.venue::text, 'NaN'),
            NULLIF(NEW.mode_of_event::text, 'NaN'),
            
            -- Turn '0' fee into empty string so it doesn't clutter search
            NULLIF(NEW.registration_fee::text, '0'),
            
            NULLIF(NEW.speakers::text, 'NaN'),
            NULLIF(NEW.faculty_coordinators::text, 'NaN'),
            NULLIF(NEW.student_coordinators::text, 'NaN'),
            NULLIF(NEW.perks::text, 'NaN'),
            NULLIF(NEW.collaboration::text, 'NaN'),
            NULLIF(NEW.description_insights::text, 'NaN')
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    ```

4.  **Create the GIN Index:**
    This index speeds up the trigram fuzzy search on the `search_text` column.
    ```sql
    CREATE INDEX CONCURRENTLY trgm_idx_events_search_text 
    ON events 
    USING GIN (search_text gin_trgm_ops);
    ```

### Installation

1.  **Frontend:**
    ```bash
    cd frontend
    npm install
    ```

2.  **Backend:**
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Frontend:**
    ```bash
    cd frontend
    npm run dev
    ```
    The frontend will be available at `http://localhost:3000`.

2.  **Backend:**
    ```bash
    cd backend
    uvicorn main:app --reload
    ```
    The backend will be available at `http://localhost:8000`.
