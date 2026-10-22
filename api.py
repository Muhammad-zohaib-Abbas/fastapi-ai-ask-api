import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.rag import answer_question_with_sources


logger = logging.getLogger(__name__)
app = FastAPI(title="PDF Knowledge Assistant")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    source: str
    page: int


class AskResponse(BaseModel):
    answer: str
    success: bool
    citations: list[Citation]


@app.get("/")
def home():
    return {"name": "PDF Knowledge Assistant", "status": "ready"}


@app.post("/ask", response_model=AskResponse)
def ask(data: AskRequest):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be blank.")

    try:
        result = answer_question_with_sources(question)
        return {**result, "success": True}
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
