
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


def retrieve_documents_old(question: str, limit: int = 3):
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
                SELECT
                    dc.id,
                    dc.content,
                    dc.metadata,
                    d.document_name,
                    d.page_number,
                    dc.embedding <=> %s AS distance
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE dc.embedding IS NOT NULL
                ORDER BY dc.embedding <=> %s
                LIMIT %s
                """,
                (query_vector, query_vector, limit),
            )

            return cursor.fetchall()




def retrieve_documents(
    question: str,
    limit: int = 3,
    max_distance: float = 0.42,
):
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
                SELECT
                    dc.id,
                    dc.content,
                    dc.metadata,
                    d.document_name,
                    d.page_number,
                    dc.embedding <=> %s AS distance
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE dc.embedding IS NOT NULL
                ORDER BY dc.embedding <=> %s
                LIMIT %s
                """,
                (query_vector, query_vector, limit),
            )

            documents = cursor.fetchall()  # Changed: store results

    # Added: discard chunks that exceed the threshold
    return [
        document
        for document in documents
        if document[5] <= max_distance
    ]



def answer_question(question: str) -> str:
    documents = retrieve_documents(question)

    if not documents:
        return "I couldn't find any relevant documents in the knowledge base."

    context_parts = []

    for (
        chunk_id,
        content,
        metadata,
        document_name,
        page_number,
        distance,
    ) in documents:
        context_parts.append(
            f"[Source: {document_name}, Page: {page_number}]\n"
            f"{content}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a helpful assistant answering questions using a PDF knowledge base.

Rules:
- Answer using only the provided context.
- Cite sources using the exact format [Source: filename, Page: number].
- Put citations next to the statements they support.
- Only cite sources explicitly provided in the context.
- Never invent filenames, page numbers, or facts.
- If the context does not contain the answer, say you could not find it.
- If the question asks where a phrase appears, list the relevant occurrences
  only when the provided context supports them.

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
