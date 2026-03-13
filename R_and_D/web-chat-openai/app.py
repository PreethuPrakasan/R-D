from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from openai import OpenAI
import jwt
import uuid
from dotenv import load_dotenv
import os


# ----------------------------
# CONFIG
# ----------------------------
SECRET = "your-secret-key"
# client = OpenAI()
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
security = HTTPBearer()

app = FastAPI()

# ----------------------------
# USER IDENTIFICATION (JWT)
# ----------------------------
def get_current_user(token=Depends(security)):
    try:
        payload = jwt.decode(token.credentials, SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ----------------------------
# IN-MEMORY SESSIONS
# ----------------------------
sessions = {}

MANDATORY_QUESTIONS = [
    "What is your age?",
    "What is your monthly income?",
    "How much do you save per month?",
    "Do you have any loans? Please specify.",
    "Do you have any existing investments?",
    "What financial goals are you trying to achieve?",
    "What is your risk appetite? (Low / Medium / High)",
]

def get_next_question(session_data):
    answers = session_data["answers"]
    for q in MANDATORY_QUESTIONS:
        if q not in answers:
            return q
    return None


# ----------------------------
# REQUEST MODELS
# ----------------------------
class ChatRequest(BaseModel):
    message: str


# ----------------------------
# JWT LOGIN (FAKE LOGIN)
# ----------------------------
@app.post("/login")
def login():
    """This simulates a login and returns a JWT."""
    user_id = str(uuid.uuid4())

    token = jwt.encode({"user_id": user_id}, SECRET, algorithm="HS256")
    return {"token": token}


# ----------------------------
# START SESSION
# ----------------------------
@app.get("/start")
def start(user_id: str = Depends(get_current_user)):
    sessions[user_id] = {"answers": {}, "history": []}
    first_q = get_next_question(sessions[user_id])
    return {"question": first_q}


# ----------------------------
# CHAT ENDPOINT
# ----------------------------
@app.post("/chat")
def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):
    session = sessions.setdefault(user_id, {"answers": {}, "history": []})
    user_message = req.message

    next_question = get_next_question(session)

    # 1️⃣ If user is answering a mandatory question
    if next_question:
        session["answers"][next_question] = user_message
        new_question = get_next_question(session)

        if new_question:
            return {"reply": new_question}

    # 2️⃣ All mandatory questions answered → Generate final plan
    if not next_question:
        messages = [
            {
                "role": "system",
                "content": "You are a financial advisor. Provide a complete, structured, and personalized financial plan based on the user's inputs."
            }
        ]

        # Provide all user answers to the LLM
        for q, a in session["answers"].items():
            messages.append({"role": "user", "content": f"{q}: {a}"})

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.4
        )

        return {"reply": response.choices[0].message["content"]}

    return {"reply": "Unexpected error occurred."}
