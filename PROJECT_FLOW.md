# Bionary Chatbot: End-to-End Project Flow

This document explains the entire data and logic flow of the Bionary Chatbot, from the user's initial query in the frontend to the final answer being displayed.

---

## 1. Frontend: User Submits a Query

The process begins when the user types a question into the chat interface and hits "Send".

-   **File:** `frontend/app/page.tsx`
-   **Action:** The `handleSubmit` function is triggered.
-   **Logic:**
    1.  It captures the user's input text.
    2.  It constructs the full API endpoint URL using an environment variable (`process.env.NEXT_PUBLIC_API_URL`).
    3.  It makes an asynchronous `POST` request to the backend's `/api/chat` endpoint, sending the user's query in the request body.
    4.  While waiting for the response, it displays a loading indicator.

```javascript
// In frontend/app/page.tsx
const response = await fetch(
  `${process.env.NEXT_PUBLIC_API_URL}/api/chat`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: input }),
  }
);
```

---

## 2. Backend: API Endpoint Receives the Request

The FastAPI backend receives the incoming request.

-   **File:** `backend/main.py`
-   **Action:** The `@app.post("/api/chat")` route is activated.
-   **Logic:**
    1.  The `chat_endpoint` function takes the `ChatRequest` Pydantic model.
    2.  It immediately passes the user's query string to the core logic handler in the `query_pipeline`.
    3.  This function acts as a simple, clean entry point to the main RAG pipeline.

```python
# In backend/main.py
@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    response = query_pipeline.handle_user_query(request.query)
    return {"answer": response}
```

---

## 3. Query Pipeline: Processing the Query

This is where the initial processing of the user's query begins.

-   **File:** `backend/query_pipeline.py`
-   **Action:** The `handle_user_query` function orchestrates the retrieval and generation steps.
-   **Logic:**
    1.  **Normalize & Filter:** The query is lowercased. Helper functions (`extract_year`, `extract_month`) attempt to find date and fee information (e.g., "free") to create hard filters for the database query.
    2.  **Extract Search Terms:** A call is made to `extract_search_terms`, which uses a simple, non-conversational Gemini prompt to pull out the core nouns or topics from the user's query (e.g., "tell me about events by jeffry" -> "jeffry"). This provides a cleaner keyword for fuzzy searching.
    3.  **Call the Retriever:** The pipeline then calls the `retriever.hybrid_query` function, passing the original query, the cleaned search terms, and any date/fee filters.

---

## 4. Retriever: Hybrid Search in the Database

This is the heart of the "Retrieval" part of RAG. **No LLM is used to write SQL.** The query is constructed in Python.

-   **File:** `backend/retriever.py`
-   **Action:** The `hybrid_query` function builds and executes a SQL query against the PostgreSQL (Neon) database.
-   **Logic:**
    1.  **Generate Embedding:** It uses a Sentence Transformer model (`BAAI/bge-base-en-v1.5`) to convert the user's query into a vector embedding (a list of numbers representing its semantic meaning).
    2.  **Construct SQL Query:** It dynamically builds a single, powerful SQL query string using Python. This query is designed to perform a "hybrid search":
        -   **Vector Search (Semantic):** Uses the `<=>` operator from the `pgvector` extension to find events with embeddings that are semantically close to the user's query embedding. This finds conceptually related events.
        -   **Fuzzy Search (Keyword):** Uses the `word_similarity` function from the `pg_trgm` extension to find events where the `search_text` column is textually similar to the user's keywords. This catches typos and variations.
        -   **Filtering:** Adds `WHERE` clauses for date ranges and fees based on the filters from the previous step.
    3.  **Rank Results:** The query uses a weighted formula to calculate a `final_score` for each event, combining the vector similarity and trigram similarity to determine relevance. The results are ordered by this score.
    4.  **Execute & Return:** The query is executed, and the function returns a list of matching event data as dictionaries.

---

## 5. Query Pipeline: Preparing the Context

The retrieved data must be cleaned and formatted before being sent to the LLM.

-   **File:** `backend/query_pipeline.py`
-   **Action:** Back in `handle_user_query`, the code iterates through the list of events returned by the retriever.
-   **Logic:**
    1.  **Handle No Results:** If the list is empty, it returns a "not found" message immediately.
    2.  **Format and Clean:** For each event, it builds a string of details. This is a critical data cleaning step:
        -   It explicitly checks for and skips any values that are `None`, `'NaN'`, or empty strings.
        -   It formats the `date_of_event` from the database's `YYYY-MM-DD` to a user-friendly `dd-mmm-yyyy` format.
        -   It converts a `registration_fee` of "0" to the word "Free".
    3.  **Build Context:** The cleaned details for all retrieved events are combined into a single, large string called `context`. This string is carefully structured to be easily parsable by the LLM.

---

## 6. Generation: Creating the Final Answer

The final step uses the LLM to generate a user-facing answer based on the retrieved data.

-   **File:** `backend/query_pipeline.py`
-   **Action:** The `handle_user_query` function calls `gemini_answer`, passing the user's original question and the clean `context` string.
-   **Logic:**
    1.  **Prompt Engineering:** The `gemini_answer` function contains a carefully crafted prompt. This prompt gives the Gemini model strict instructions:
        -   You are a university assistant.
        -   Answer the question **using only the provided context.** This prevents the LLM from making things up.
        -   **Strict Formatting Rules:** The prompt commands the model to **always use tables** and provides visual examples of a "Horizontal Table" (for multiple events) and a "Vertical Table" (for a single event). It explicitly forbids other formats like bullet points or markdown headers.
    2.  **LLM Call:** The prompt, now filled with the context, is sent to the Gemini API.
    3.  **Generate Answer:** The LLM generates the final answer, adhering to the formatting rules and using only the data it was given.

---

## 7. Backend: Logging the Interaction

Before sending the response back, the backend logs the interaction for auditing and analysis.

-   **File:** `backend/main.py`
-   **Action:** Inside the `chat_endpoint` function, after the answer is generated.
-   **Logic:**
    1.  The current timestamp is captured and converted to the 'Asia/Kolkata' (IST) timezone.
    2.  The date and time are formatted into `DD-MM-YYYY` and `HH:MM:SS` strings, respectively.
    3.  A new `Log` object is created with the user's `question`, the generated `answer`, the `sql_query` used to fetch the data, and the formatted `date` and `time`.
    4.  The new log entry is saved to the `logs` table in the database.

---

## 8. Frontend: Displaying the Response

The backend sends the final generated answer back to the frontend.

-   **File:** `frontend/app/page.tsx`
-   **Action:** The `fetch` call made in Step 1 resolves.
-   **Logic:**
    1.  The response body is parsed as JSON.
    2.  The `answer` string is extracted from the JSON.
    3.  The frontend updates its state, adding the agent's message to the chat history.
    4.  React renders the new message, and the user sees the final, table-formatted response.

This completes the end-to-end flow of a single user query.