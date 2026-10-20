
from google import genai
from google.genai import types
from pgvector import Vector
from pgvector.psycopg import register_vector

from app.config import GEMINI_API_KEY
from app.database import get_connection
from app.embeddings import generate_embedding


client = genai.Client(api_key=GEMINI_API_KEY)
# GENERATION_MODEL = "gemini-flash-latest"
GENERATION_MODEL = "gemini-3.6-flash"


def retrieve_documents(question: str, limit: int = 3):
    query_embedding = generate_embedding(
        question,
        task_type="RETRIEVAL_QUERY",
    )
    query_vector = Vector(query_embedding)

    with get_connection() as connection:
        register_vector(connection)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, content,
                       embedding <=> %s AS distance
                FROM document_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (query_vector, query_vector, limit),
            )

            return cursor.fetchall()


def answer_question(question: str) -> str:
    documents = retrieve_documents(question)

    if not documents:
        return "I couldn't find any documents in the knowledge base."

    context = "\n\n".join(
        f"Document {doc_id}: {content}"
        for doc_id, content, distance in documents
    )

    prompt = f"""
You are a helpful assistant answering questions from a document
knowledge base.

Use only the information in the context below.
If the context does not contain enough information to answer,
say that you could not find the answer in the available documents.
Do not invent facts.

Context:
{context}

Question:
{question}

Answer:
"""

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            )
        ),
    )
    return response.text or "Gemini did not return a text answer."
