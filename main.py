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
from fastapi import FastAPI, Request, Form, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
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
@app.post("/api/chat")
async def chat(request: Request):
    try:
        # Parse the request body
        data = await request.json()
        user_message = data.get("message")
        
        if not user_message:
            return JSONResponse(
                status_code=400, 
                content={"error": "No message provided"}
            )
        
        if not agent:
            return JSONResponse(
                status_code=500, 
                content={"error": "Agent not initialized properly"}
            )
            
        # Process the message with the ReAct Agent
        response = agent.chat(user_message)
        
        # Ensure the response is a string
        if not isinstance(response, str):
            logger.warning(f"Agent returned non-string response: {type(response)}. Converting to string.")
            if isinstance(response, dict):
                # For specialty API responses, extract useful information
                if "specialties" in response:
                    specialty_list = []
                    for specialty in response.get("specialties", []):
                        desc = specialty.get("DESCRIPTION", "Unknown specialty")
                        specialty_list.append(desc)
                    
                    if specialty_list:
                        # Check if this is a full list request
                        is_full_list = response.get("is_full_list", False)
                        
                        # Format the response for better readability
                        if len(specialty_list) > 10 and not is_full_list:
                            # Show first 5 specialties if there are many and not a full list request
                            formatted_response = f"We have {len(specialty_list)} medical specialties available. Here are some examples:\n\n"
                            for i in range(min(5, len(specialty_list))):
                                formatted_response += f"• {specialty_list[i]}\n"
                            
                            formatted_response += f"\nWould you like to see the full list of specialties or are you looking for a specific one?"
                            response = formatted_response
                        else:
                            # Show all specialties for full list requests or when there are few specialties
                            if is_full_list:
                                formatted_response = f"Here's the complete list of all {len(specialty_list)} specialties:\n\n"
                            else:
                                formatted_response = "Here are all our available specialties:\n\n"
                            
                            # Sort alphabetically for better readability
                            specialty_list.sort()
                            
                            for specialty in specialty_list:
                                formatted_response += f"• {specialty}\n"
                            response = formatted_response
                    else:
                        response = "I couldn't find any matching specialties."
                else:
                    # Generic dictionary conversion
                    response = f"Here's what I found: {json.dumps(response)}"
            else:
                # For any other non-string type
                response = str(response)
        
        return JSONResponse(content={"response": response})
        
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"error": f"An error occurred: {str(e)}"}
        )

# WebSocket endpoint for real-time logging
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming log messages to clients
    """
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            logger.info(f"Received WebSocket message: {user_message}")
            
            if not user_message:
                await websocket.send_json({"error": "No message provided"})
                continue
                
            if not agent:
                await websocket.send_json({"error": "Agent not initialized properly"})
                continue
            
            # Process with ReAct Agent
            try:
                response = agent.chat(user_message)
                
                # Ensure the response is a string
                if not isinstance(response, str):
                    logger.warning(f"Agent returned non-string response: {type(response)}. Converting to string.")
                    if isinstance(response, dict):
                        # For specialty API responses, extract useful information
                        if "specialties" in response:
                            specialty_list = []
                            for specialty in response.get("specialties", []):
                                desc = specialty.get("DESCRIPTION", "Unknown specialty")
                                specialty_list.append(desc)
                            
                            if specialty_list:
                                # Check if this is a full list request
                                is_full_list = response.get("is_full_list", False)
                                
                                # Format the response for better readability
                                if len(specialty_list) > 10 and not is_full_list:
                                    # Show first 5 specialties if there are many and not a full list request
                                    formatted_response = f"We have {len(specialty_list)} medical specialties available. Here are some examples:\n\n"
                                    for i in range(min(5, len(specialty_list))):
                                        formatted_response += f"• {specialty_list[i]}\n"
                                    
                                    formatted_response += f"\nWould you like to see the full list of specialties or are you looking for a specific one?"
                                    response = formatted_response
                                else:
                                    # Show all specialties for full list requests or when there are few specialties
                                    if is_full_list:
                                        formatted_response = f"Here's the complete list of all {len(specialty_list)} specialties:\n\n"
                                    else:
                                        formatted_response = "Here are all our available specialties:\n\n"
                                    
                                    # Sort alphabetically for better readability
                                    specialty_list.sort()
                                    
                                    for specialty in specialty_list:
                                        formatted_response += f"• {specialty}\n"
                                    response = formatted_response
                            else:
                                response = "I couldn't find any matching specialties."
                        else:
                            # Generic dictionary conversion
                            response = f"Here's what I found: {json.dumps(response)}"
                    else:
                        # For any other non-string type
                        response = str(response)
                
                # Send response back to client
                await websocket.send_json({"response": response})
                logger.info(f"Sent WebSocket response: {response[:100]}...")
                
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                logger.error(error_msg)
                await websocket.send_json({"error": error_msg})
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        # Try to send error message if connection is still open
        try:
            await websocket.send_json({"error": f"An error occurred: {str(e)}"})
        except:
            pass

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
    try:
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}") 