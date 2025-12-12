# Bionary Fullstack Agent

This project is a fullstack application with a React-based frontend and a Python-based backend.

## Project Structure

The project is divided into two main parts:

- `frontend/`: A [Next.js](https://nextjs.org/) application.
- `backend/`: A [FastAPI](https://fastapi.tiangolo.com/) application.

## Backend

The backend is a FastAPI application that provides a chat API and an API for adding events.

### Features

- **Chat API (`/api/chat`):** This endpoint uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions about university events. It takes a natural language query, retrieves relevant data from a PostgreSQL database, and uses the Google Gemini language model to generate an answer.
- **Add Event API (`/api/add-event`):** This is a protected endpoint for adding new events. It generates and stores vector embeddings for the events to make them searchable.
- **Authentication:** Authentication is handled using JSON Web Tokens (JWT).

### Technologies

- **FastAPI:** A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **PostgreSQL:** A powerful, open source object-relational database system.
- **pgvector:** An extension for PostgreSQL that enables storing and querying of vector embeddings.
- **Google Gemini:** A family of large language models developed by Google AI.

## Frontend

The frontend is a Next.js application built with React.

*Further details about the frontend will be added here.*

## Utilities

A Streamlit application is available at `pages/new_event.py`. This standalone script provides a user-friendly interface for inputting event details, which are then saved to the database and indexed for semantic search.

### Running the Event Management Utility

To run the Streamlit application, execute the following command:

```bash
streamlit run pages/new_event.py
```

## Getting Started

### Prerequisites

*   Node.js and npm (for the frontend)
*   Python 3.7+ and pip (for the backend)
*   PostgreSQL (with the `pgvector` extension)

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
