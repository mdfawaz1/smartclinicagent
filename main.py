#!/usr/bin/env python3
"""
FastAPI server for the SmartClinic ReAct Agent.
This script creates a RESTful API around the agent for HTTP interactions.
"""

import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from react_agent import ReActAgent

# Custom logging handler to capture logs
class WebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
        self.clients = set()
        self.loop = None  # Will store event loop reference when available
        
    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        
        # Store the log but don't try to broadcast it immediately
        # Broadcasting will happen when clients connect
        # This avoids the "no running event loop" error
        
    async def broadcast(self, message):
        for client in list(self.clients):
            try:
                await client.send_text(json.dumps({"log": message}))
            except Exception:
                self.clients.remove(client)
    
    def add_client(self, websocket):
        self.clients.add(websocket)
        
    def remove_client(self, websocket):
        if websocket in self.clients:
            self.clients.remove(websocket)

# Set up logging to display all steps
ws_handler = WebSocketLogHandler()
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("api")
logger.addHandler(ws_handler)

# Load environment variables
load_dotenv()

# Get configuration from environment variables
llm_endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:1234/v1/chat/completions")
specialty_api_endpoint = os.getenv("SPECIALTY_API_ENDPOINT", "http://eserver/api/his/AppointmentsAPI/InitAll")
specialty_api_token = os.getenv("SPECIALTY_API_TOKEN")

# Check if token is available
if not specialty_api_token:
    logger.warning("SPECIALTY_API_TOKEN not found in environment variables. Using default token.")
    specialty_api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciI6IjB4MzEzNDM0MzdCMEE2RjcxQS0yRkM0LTRENTYtOTcwOS1EOTlBMjQ1REYyQkIiLCJleHAiOjE3NTA4NjE2MTgsImlzcyI6Iml2aXZhY2FyZS5jb20iLCJhdWQiOiJpdml2YWNhcmUuY29tIn0.MeN6uRSfZkCownAcued_BFXOMPnf8wPHUBUBI2yTkFk"

# Initialize the ReAct Agent with debug mode
agent = ReActAgent(
    llm_endpoint=llm_endpoint,
    specialty_api_endpoint=specialty_api_endpoint,
    specialty_api_token=specialty_api_token,
    debug_mode=True  # Enable debug mode to show all steps
)

# Create FastAPI app
app = FastAPI(
    title="SmartClinic ReAct Agent API",
    description="API for interacting with the hospital chatbot using ReAct paradigm",
    version="1.0.0"
)

# Define request and response models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

# Create endpoint for chat interactions
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Chat endpoint that processes user messages through the ReAct agent
    
    Args:
        request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse with the agent's response
    """
    logger.info(f"Received message: {request.message}")
    
    # Process the user's message through the ReAct agent
    response = agent.chat(request.message)
    
    return ChatResponse(response=response)

# WebSocket endpoint for real-time logging
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for streaming log messages to clients
    """
    try:
        await websocket.accept()
        logger.info(f"WebSocket client connected")
        
        # Add client to the handler
        ws_handler.add_client(websocket)
        
        # Send all previous logs
        for log in ws_handler.logs:
            await websocket.send_text(json.dumps({"log": log}))
            await asyncio.sleep(0.01)  # Small delay to avoid overwhelming the client
        
        # Keep the connection alive
        while True:
            try:
                # Wait for any message from the client (ping)
                data = await websocket.receive_text()
                # Echo it back as a pong
                await websocket.send_text(json.dumps({"pong": data}))
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected")
                ws_handler.remove_client(websocket)
                break
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        ws_handler.remove_client(websocket)

# Mount a simple HTML interface
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_chat_interface(request: Request):
    """Serve the chat interface HTML page"""
    return templates.TemplateResponse("chat.html", {"request": request})

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    # Start the FastAPI server
    logger.info("Starting SmartClinic ReAct Agent API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 