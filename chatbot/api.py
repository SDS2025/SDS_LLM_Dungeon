from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from dungeonbot import DungeonMaster

app = FastAPI()

# CORS für lokale Entwicklung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary für Session-spezifische Agenten
session_agents: Dict[str, DungeonMaster] = {}

class ChatMessage(BaseModel):
    message: str
    chat_history: List[str] = []
    session_id: str

class ChatResponse(BaseModel):
    response: str
    state: str
    log_message: Dict[str, Any]

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    try:
        # Prüfen ob eine Session-ID existiert, sonst neue erstellen
        if chat_message.session_id not in session_agents:
            session_agents[chat_message.session_id] = DungeonMaster()
        
        agent = session_agents[chat_message.session_id]
        response, log_message = agent.get_response(
            chat_message.message, 
            chat_message.chat_history
        )
        return ChatResponse(
            response=response,
            state=agent.state,
            log_message=log_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 