from google import genai
from google.genai import errors
from google.genai import types
from pgvector import Vector
from pgvector.psycopg import register_vector

from app.config import GEMINI_API_KEY
from app.database import get_connection
from app.embeddings import generate_embedding


client = genai.Client(api_key=GEMINI_API_KEY)
GENERATION_MODEL = "gemini-3.6-flash"
FALLBACK_GENERATION_MODEL = "gemini-flash-latest"
NO_DOCUMENTS_ANSWER = "I couldn't find any relevant documents in the knowledge base."


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
                LEFT JOIN documents d ON d.id = dc.document_id
                WHERE dc.embedding IS NOT NULL
                ORDER BY dc.embedding <=> %s
                LIMIT %s
                """,
                (query_vector, query_vector, limit),
            )
            documents = cursor.fetchall()

    return [document for document in documents if document[5] <= max_distance]


def answer_question_with_sources(question: str) -> dict:
    documents = retrieve_documents(question)
    if not documents:
        return {"answer": NO_DOCUMENTS_ANSWER, "citations": []}

    context_parts = []
    citations = []
    for chunk_id, content, metadata, document_name, page_number, _distance in documents:
        metadata = metadata or {}
        source = document_name or metadata.get("source") or f"legacy_chunk_{chunk_id}"
        page = page_number or metadata.get("page_number") or 1
        citation = {"source": str(source), "page": int(page)}
        if citation not in citations:
            citations.append(citation)
        context_parts.append(
            f"[Source: {citation['source']}, Page: {citation['page']}]\n{content}"
        )

    context = "\n\n".join(context_parts)
    prompt = f"""You answer questions using a PDF knowledge base.
Use only the context below. Put citations next to the claims they support using
the exact format [Source: filename, Page: number]. Cite only sources shown in the
context. Never invent facts, filenames, or page numbers. If the context does not
answer the question, say you could not find the answer in the available documents.

Context:
{context}

Question:
{question}

Answer:
"""
    generation_config = types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        )
    )
    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=generation_config,
        )
    except errors.APIError as error:
        if (
            getattr(error, "code", None) != 503
            or FALLBACK_GENERATION_MODEL == GENERATION_MODEL
        ):
            raise
        response = client.models.generate_content(
            model=FALLBACK_GENERATION_MODEL,
            contents=prompt,
            config=generation_config,
        )
    return {
        "answer": response.text or "Gemini did not return a text answer.",
        "citations": citations,
    }


def answer_question(question: str) -> str:
    """Compatibility wrapper used by the terminal RAG script."""
    return answer_question_with_sources(question)["answer"]
