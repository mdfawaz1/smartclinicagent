# SmartClinic API Documentation

This document describes how to set up and use the SmartClinic ReAct Agent API.

## Setup Instructions

1. **Ensure Anaconda Environment is Activated**

```bash
conda activate agent
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure Environment Variables**

Make sure your `.env` file has the necessary configuration:

```
# Local LLM Configuration
LLM_ENDPOINT=http://localhost:1234/v1/chat/completions

# Doctor Specialty API Configuration
SPECIALTY_API_ENDPOINT=http://eserver/api/his/AppointmentsAPI/InitAll
SPECIALTY_API_TOKEN=your_token_here
```

4. **Run the FastAPI Server**

```bash
python main.py
```

The server will start on http://localhost:8000

## API Endpoints

### Chat Endpoint

**Endpoint**: `/api/chat`  
**Method**: POST  
**Description**: Process user messages through the ReAct agent

#### Request Format

```json
{
  "message": "What cardiology services do you offer?"
}
```

#### Response Format

```json
{
  "response": "We offer a variety of cardiology services including cardiac consultations, ECG, echocardiography, stress tests, and cardiac monitoring."
}
```

## Example cURL Commands

### Send a Chat Message

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What specialties are available?"}'
```

### Query for a Specific Specialty

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Do you have cardiologists?"}'
```

## Web Interface

A simple web interface is available at http://localhost:8000/

You can interact with the chatbot through this interface without needing to make API calls directly. 