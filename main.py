from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv
from database import init_db, load_history, save_history, clear_history, append_context, get_user_chats
import os
import base64
import fitz  # PyMuPDF
import bcrypt
import ollama as ollama_client
import re
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()
init_db()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# CUSTOM PERSONA — change this to whatever you want!
SYSTEM_PROMPT = """You are Zuri, a female AI assistant. You are the user's intelligent, witty, and caring best friend.

PERSONALITY:
- You are a girl. You talk like an intelligent, confident young woman.
- You are friendly, warm, and genuinely caring. You make the user feel like they're talking to their closest female friend.
- You have a good sense of humor — you crack jokes, tease affectionately, and use light sarcasm.
- You are super smart and knowledgeable. You can help with coding, life advice, daily problems, and random questions.
- You remember things from the conversation and reference them naturally.
- You use emojis sparingly but naturally 😊

LANGUAGE RULES (CRITICAL — FOLLOW THESE EXACTLY, NO EXCEPTIONS):
- There are only TWO languages you respond in: English or বাংলা (Bengali script).
- If the user writes in English → respond 100% in English. No Bengali words at all.
- If the user writes in Bengali script (বাংলা) → respond 100% in Bengali script (বাংলা). No English words at all.
- If the user writes in Banglish (Bengali words typed in English letters like "kemon acho") → treat this as Bengali and respond in বাংলা (Bengali script). NOT in Banglish, NOT in English.
- NEVER mix English and Bengali in the same response.
- NEVER add translations in parentheses like "(this means X)".
- NEVER respond in Banglish (English letters for Bengali words). Always use proper বাংলা script for Bengali.
- Pick ONE language per response and use it completely.

CODING TUTOR RULES:
- When explaining code, break it down step by step like you're teaching a friend, not lecturing.
- Always include examples when explaining concepts.
- If the user's code has a bug, tease them gently first, then fix it properly.
- Use code blocks with proper syntax highlighting.

EXAMPLE CONVERSATIONS:

Bengali (when user types in Banglish or বাংলা):
- User: "kire kemon acho" → You: "আমি তো ভালোই আছি! তুমি বলো, কী খবর তোমার? আজকে কী করছো? 😊"
- User: "ami boshe achi" → You: "বসে আছো? একা একা? আচ্ছা বলো, কিছু মজার করা যাক নাকি? আমি তো আছিই তোমার সাথে গল্প করতে! 😄"
- User: "kisu korchi na" → You: "কিছু করছো না মানে? তাহলে তো আমার সাথেই আড্ডা দাও! বলো কী বিষয়ে কথা বলবে — কোডিং, লাইফ, নাকি গসিপ? 😏"
- User: "help lagbe" → You: "বলো বলো, কী সমস্যা? আমি তো এই জন্যই আছি! �"

English:
- User: "explain recursion" → You: "Recursion is when a function calls itself... kind of like when you keep opening the fridge hoping new food appeared. Let me show you a proper example 😏"
- User: "hey what's up" → You: "Hey! Not much, just waiting for you to show up 😄 What's going on? Need help with something or just wanna chat?"
"""

PERSONA_PROMPTS = {
    "zuri": SYSTEM_PROMPT,
    "tutor": """You are a strict but supportive Coding Tutor. You focus only on programming and computer science topics.
- Explain concepts step by step with code examples.
- When the student makes a mistake, point it out clearly and explain why it's wrong.
- Use analogies to make complex topics simple.
- Always encourage the student to try solving problems before giving answers.
- Respond in the same language the user writes in (English or Bengali).""",
    "therapist": """You are a compassionate Therapist and emotional support companion.
- Listen actively and validate the user's feelings.
- Ask thoughtful follow-up questions to help the user reflect.
- Never diagnose or prescribe. You are a supportive friend, not a medical professional.
- Be warm, gentle, and non-judgmental.
- Respond in the same language the user writes in (English or Bengali).""",
    "study_buddy": """You are a smart Study Buddy who helps students prepare for exams.
- Break down complex topics into easy-to-understand points.
- Create mnemonics and memory tricks.
- Quiz the user on topics they want to revise.
- Summarize long chapters into key bullet points.
- Respond in the same language the user writes in (English or Bengali).""",
    "creative": """You are a Creative Writer and storyteller.
- Help the user write stories, poems, scripts, and creative content.
- Be imaginative, expressive, and artistic.
- Offer multiple creative directions for the user to choose from.
- Give constructive feedback on the user's writing.
- Respond in the same language the user writes in (English or Bengali).""",
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"
    user_id: str = "default_user"
    image_base64: Optional[str] = None
    ai_model: str = "gemini"
    persona: str = "zuri"

class ChatEditRequest(BaseModel):
    message: str
    message_index: int
    session_id: str = "default_user"
    user_id: str = "default_user"
    image_base64: Optional[str] = None
    ai_model: str = "gemini"
    persona: str = "zuri"

class AuthRequest(BaseModel):
    username: str
    password: str

# Check if history is too long and summarize it
def summarize_history_if_needed(session_id: str, history: list[dict]):
    if len(history) > 10:
        # Ask Gemini to summarize
        summary_prompt = "Please summarize the following conversation history briefly. Focus on key details the user shared and important context. \n\n"
        for turn in history:
            summary_prompt += f"User: {turn['user']}\nZuri: {turn['bot']}\n"
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=summary_prompt,
            )
            summary = response.text
             # Create a single "memory" message
            new_history = [{"user": "[System automatically summarized previous conversation]", "bot": f"I remember: {summary}"}]
            save_history(session_id, new_history, user_id=req.user_id)
            return new_history
        except Exception as e:
            print(f"Summarization error: {e}")
            return history
    return history

@app.post("/chat")
def chat(req: ChatRequest):
    # Load memory from DB
    history, context = load_history(req.session_id, req.user_id)
    history = summarize_history_if_needed(req.session_id, history)
    
    # Auto-title on first message
    new_title = None
    if len(history) == 0:
        new_title = req.message[:30] + "..." if len(req.message) > 30 else req.message

    # Build full conversation context
    contents = []
    
    # Text prompt construction
    sys_prompt = PERSONA_PROMPTS.get(req.persona, SYSTEM_PROMPT)
    if context:
        sys_prompt += f"\n\n[USER DOCUMENT CONTEXT]\nThe user has provided the following documents. Use this to answer their questions if relevant:\n{context}\n[/USER DOCUMENT CONTEXT]"
        
    full_text_conversation = sys_prompt + "\n"
    for turn in history:
        full_text_conversation += f"User: {turn['user']}\nZuri: {turn['bot']}\n"
    full_text_conversation += f"User: {req.message}\nZuri:"
    
    contents.append(full_text_conversation)

    # Add image if provided
    if req.image_base64:
        try:
            # Strip the data:image/jpeg;base64, prefix if present
            if "," in req.image_base64:
                b64_data = req.image_base64.split(",")[1]
            else:
                b64_data = req.image_base64
            
            image_bytes = base64.b64decode(b64_data)
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        except Exception as e:
            print(f"Image decode error: {e}")

    # STREAMING RESPONSE
    def stream_reply():
        full_reply = ""
        error_occurred = False
        try:
            if req.ai_model == "ollama":
                # --- Ollama Local Streaming ---
                ollama_messages = [{"role": "system", "content": sys_prompt}]
                for turn in history:
                    ollama_messages.append({"role": "user", "content": turn["user"]})
                    ollama_messages.append({"role": "assistant", "content": turn["bot"]})
                
                user_msg = {"role": "user", "content": req.message}
                local_model = "llama3.1"
                if req.image_base64:
                    # Ollama expects raw base64 string without data URI prefix
                    b64_str = req.image_base64.split(",")[1] if "," in req.image_base64 else req.image_base64
                    user_msg["images"] = [b64_str]
                    local_model = "llava" # Route to vision model when an image is attached
                
                ollama_messages.append(user_msg)

                for chunk in ollama_client.chat(
                    model=local_model,
                    messages=ollama_messages,
                    stream=True,
                ):
                    token = chunk["message"]["content"] or ""
                    full_reply += token
                    yield token
            else:
                # --- Gemini Cloud Streaming ---
                for chunk in client.models.generate_content_stream(
                    model="gemini-2.5-flash-lite",
                    contents=contents,
                ):
                    token = chunk.text or ""
                    full_reply += token
                    yield token
        except Exception as e:
            error_occurred = True
            error_msg = f"\n\n*(Error: API Rate limit reached or connection failed. Details: {str(e)})*"
            full_reply += error_msg
            yield error_msg

        # Save to memory after full reply is streamed
        if not error_occurred and full_reply.strip():
            updated = history + [{"user": req.message, "bot": full_reply.strip()}]
            save_history(req.session_id, updated, title=new_title, user_id=req.user_id)

    return StreamingResponse(stream_reply(), media_type="text/plain")

@app.post("/edit-chat")
def edit_chat(req: ChatEditRequest):
    # Load memory from DB
    history, context = load_history(req.session_id, req.user_id)
    
    # Truncate history up to the message_index
    if req.message_index < len(history):
        history = history[:req.message_index]
        
    history = summarize_history_if_needed(req.session_id, history)
    
    new_title = None
    if len(history) == 0:
        new_title = req.message[:30] + "..." if len(req.message) > 30 else req.message

    # Build full conversation context
    contents = []
    
    sys_prompt = PERSONA_PROMPTS.get(req.persona, SYSTEM_PROMPT)
    if context:
        sys_prompt += f"\n\n[USER DOCUMENT CONTEXT]\nThe user has provided the following documents. Use this to answer their questions if relevant:\n{context}\n[/USER DOCUMENT CONTEXT]"
        
    full_text_conversation = sys_prompt + "\n"
    for turn in history:
        full_text_conversation += f"User: {turn['user']}\nZuri: {turn['bot']}\n"
    full_text_conversation += f"User: {req.message}\nZuri:"
    
    contents.append(full_text_conversation)

    # Add image if provided
    if req.image_base64:
        try:
            if "," in req.image_base64:
                b64_data = req.image_base64.split(",")[1]
            else:
                b64_data = req.image_base64
            
            image_bytes = base64.b64decode(b64_data)
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        except Exception as e:
            print(f"Image decode error: {e}")

    def stream_reply():
        full_reply = ""
        error_occurred = False
        try:
            if req.ai_model == "ollama":
                ollama_messages = [{"role": "system", "content": sys_prompt}]
                for turn in history:
                    ollama_messages.append({"role": "user", "content": turn["user"]})
                    ollama_messages.append({"role": "assistant", "content": turn["bot"]})
                
                user_msg = {"role": "user", "content": req.message}
                local_model = "llama3.1"
                if req.image_base64:
                    b64_str = req.image_base64.split(",")[1] if "," in req.image_base64 else req.image_base64
                    user_msg["images"] = [b64_str]
                    local_model = "llava" 
                
                ollama_messages.append(user_msg)

                for chunk in ollama_client.chat(model=local_model, messages=ollama_messages, stream=True):
                    token = chunk["message"]["content"] or ""
                    full_reply += token
                    yield token
            else:
                for chunk in client.models.generate_content_stream(model="gemini-2.5-flash-lite", contents=contents):
                    token = chunk.text or ""
                    full_reply += token
                    yield token
        except Exception as e:
            error_occurred = True
            error_msg = f"\n\n*(Error: API Rate limit reached or connection failed. Details: {str(e)})*"
            full_reply += error_msg
            yield error_msg

        if not error_occurred and full_reply.strip():
            updated = history + [{"user": req.message, "bot": full_reply.strip()}]
            save_history(req.session_id, updated, title=new_title, user_id=req.user_id)

    return StreamingResponse(stream_reply(), media_type="text/plain")

from database import register_user, get_user_by_username

@app.post("/register")
def register(req: AuthRequest):
    hashed = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = register_user(req.username, hashed)
    if not user_id:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"status": "success", "user_id": user_id, "username": req.username}

@app.post("/login")
def login(req: AuthRequest):
    user = get_user_by_username(req.username)
    if not user or not bcrypt.checkpw(req.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"status": "success", "user_id": user["id"], "username": user["username"]}

@app.post("/upload-doc")
async def upload_doc(session_id: str = Form(...), user_id: str = Form("default_user"), file: UploadFile = File(...)):
    text_content = ""
    try:
        if file.filename.endswith(".pdf"):
            pdf_bytes = await file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text_content += page.get_text()
            doc.close()
        elif file.filename.endswith(".txt"):
            text_content = (await file.read()).decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Only PDF and TXT files supported.")
        
        # Limit extracted text length to avoid blowing up the context window completely
        MAX_CHARS = 10000 
        if len(text_content) > MAX_CHARS:
            text_content = text_content[:MAX_CHARS] + "...[TRUNCATED]"

        if text_content.strip():
            append_context(session_id, f"Document: {file.filename}\n{text_content}", user_id=user_id)
            return {"status": "success", "message": f"Extracted {len(text_content)} characters from {file.filename}"}
        else:
            return {"status": "error", "message": "No text could be extracted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/chats")
def list_chats(user_id: str):
    return {"chats": get_user_chats(user_id)}

@app.delete("/chat/{session_id}")
def reset_chat(session_id: str):
    clear_history(session_id)
    return {"status": "cleared"}

@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    history, _ = load_history(session_id)
    return {"history": history}

class YouTubeRequest(BaseModel):
    url: str
    ai_model: str = "gemini"

@app.post("/summarize-youtube")
def summarize_youtube(req: YouTubeRequest):
    # Extract video ID from URL
    match = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', req.url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    video_id = match.group(1)
    
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        text = " ".join([entry.text for entry in transcript.snippets])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch transcript: {str(e)}")
    
    # Limit transcript length
    if len(text) > 15000:
        text = text[:15000] + "...[TRUNCATED]"
    
    prompt = f"""Summarize this YouTube video transcript clearly and concisely. Include:
1. Main topic
2. Key points (bullet points)
3. Important details or takeaways

Transcript:
{text}"""
    
    def stream_summary():
        try:
            if req.ai_model == "ollama":
                for chunk in ollama_client.chat(model="llama3", messages=[{"role": "user", "content": prompt}], stream=True):
                    yield chunk["message"]["content"] or ""
            else:
                for chunk in client.models.generate_content_stream(model="gemini-2.5-flash-lite", contents=prompt):
                    yield chunk.text or ""
        except Exception as e:
            yield f"\n\n*(Error: {str(e)})*"
    
    return StreamingResponse(stream_summary(), media_type="text/plain")

class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 5
    ai_model: str = "gemini"

@app.post("/generate-quiz")
def generate_quiz(req: QuizRequest):
    prompt = f"""Generate exactly {req.num_questions} flashcard quiz questions about: {req.topic}

Return ONLY valid JSON in this exact format, no other text:
[
  {{"question": "What is X?", "answer": "X is..."}},
  {{"question": "Explain Y", "answer": "Y is..."}}
]"""
    
    try:
        if req.ai_model == "ollama":
            response = ollama_client.chat(model="llama3", messages=[{"role": "user", "content": prompt}])
            return {"quiz": response["message"]["content"]}
        else:
            response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
            return {"quiz": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve the frontend folder as static files on the root
# This must be at the very bottom so it doesn't override API routes
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

