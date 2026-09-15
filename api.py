from fastapi import FastAPI, HTTPException
# import requests 
from client.ai import ask_ai
from pydantic import BaseModel

class RequestData(BaseModel):
    question: str

class ResposeData(BaseModel):
    answer: str
    success: bool


app = FastAPI()

@app.get("/")

def home():
    return{
        "Model": "gemini ai model"
    }

@app.post("/ask", response_model=ResposeData)
def ask(data: RequestData):
    try:
        response = ask_ai(data.question)
        # response = 10 / 0
        # return response.json()
        return {
            "answer": response,
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI resuest field {str(e)}"
        )

    