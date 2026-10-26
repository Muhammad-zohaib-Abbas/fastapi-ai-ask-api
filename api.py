import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel, Field

from app.rag import answer_question_with_sources
from scripts.ingest_pdf import ingest_pdf
from app.database import get_connection
import json


logger = logging.getLogger(__name__)
app = FastAPI(title="PDF Knowledge Assistant")


# class AskRequest(BaseModel):
#     question: str = Field(min_length=1, max_length=4000)


# class Citation(BaseModel):
#     source: str
#     page: int


# class AskResponse(BaseModel):
#     answer: str
#     success: bool
#     citations: list[Citation]

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class Citation(BaseModel):
    source: str
    page: int


class AskResponse(BaseModel):
    answer: str
    success: bool
    citations: list[Citation]
    conversation_id: UUID

class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: str


@app.get("/")
def home():
    return {"name": "PDF Knowledge Assistant", "status": "ready"}


@app.post("/ask", response_model=AskResponse)

def ask(data: AskRequest):
    question = data.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question must not be blank.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                conversation_id = data.conversation_id

                # Create a conversation if the client did not provide one.
                if conversation_id is None:
                    cursor.execute(
                        """
                        INSERT INTO conversations (title)
                        VALUES (%s)
                        RETURNING id;
                        """,
                        (question[:80] or "New conversation",),
                    )
                    conversation_id = cursor.fetchone()[0]
                else:
                    cursor.execute(
                        """
                        SELECT id
                        FROM conversations
                        WHERE id = %s;
                        """,
                        (conversation_id,),
                    )

                    if cursor.fetchone() is None:
                        raise HTTPException(
                            status_code=404,
                            detail="Conversation not found.",
                        )

                # Load the most recent 10 messages.
                cursor.execute(
                    """
                    SELECT role, content
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT 10;
                    """,
                    (conversation_id,),
                )
                history = [
                    {"role": role, "content": content}
                    for role, content in reversed(cursor.fetchall())
                ]

        # This call will use the conversation history after we update app/rag.py.
        result = answer_question_with_sources(
            question,
            conversation_history=history,
        )

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO messages
                        (conversation_id, role, content, citations)
                    VALUES (%s, 'user', %s, '[]'::jsonb);
                    """,
                    (conversation_id, question),
                )

                cursor.execute(
                    """
                    INSERT INTO messages
                        (conversation_id, role, content, citations)
                    VALUES (%s, 'assistant', %s, %s::jsonb);
                    """,
                    (
                        conversation_id,
                        result["answer"],
                        json.dumps(result["citations"]),
                    ),
                )

                cursor.execute(
                    """
                    UPDATE conversations
                    SET updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (conversation_id,),
                )

        return {
            **result,
            "success": True,
            "conversation_id": conversation_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        if getattr(error, "code", None) == 503:
            logger.warning("Gemini is temporarily unavailable: %s", error)
            raise HTTPException(
                status_code=503,
                detail="The AI service is temporarily busy. Please retry shortly.",
                headers={"Retry-After": "5"},
            ) from error

        logger.exception("Failed to answer question")
        raise HTTPException(
            status_code=500,
            detail="Unable to answer the question right now.",
        ) from error




@app.post("/documents/upload")
def upload_pdf(file: UploadFile = File(...)):
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]

    if not filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file.",
        )

    max_size = 20 * 1024 * 1024  # 20 MB

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / filename
            total_size = 0

            with pdf_path.open("wb") as destination:
                while True:
                    chunk = file.file.read(1024 * 1024)

                    if not chunk:
                        break

                    total_size += len(chunk)

                    if total_size > max_size:
                        raise HTTPException(
                            status_code=413,
                            detail="PDF must not exceed 20 MB.",
                        )

                    destination.write(chunk)

            if total_size == 0:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file is empty.",
                )

            ingest_pdf(str(pdf_path))

        return {
            "success": True,
            "filename": filename,
            "message": "PDF processed and saved successfully.",
        }

    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except Exception as error:
        logger.exception("PDF ingestion failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the PDF right now.",
        ) from error
    finally:
        file.file.close()


from app.database import get_connection


@app.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(data: ConversationCreate):
    title = data.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Conversation title must not be blank.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversations (title)
                    VALUES (%s)
                    RETURNING id, title, created_at;
                    """,
                    (title,),
                )
                conversation = cursor.fetchone()

        return {
            "id": conversation[0],
            "title": conversation[1],
            "created_at": conversation[2].isoformat(),
        }

    except Exception as error:
        logger.exception("Failed to create conversation")
        raise HTTPException(
            status_code=500,
            detail="Unable to create a conversation right now.",
        ) from error