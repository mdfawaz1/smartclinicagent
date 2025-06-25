# SmartClinic ReAct Agent

A ReAct (Reason-Act-Observe) agent for a hospital chatbot that interacts with a local LLM and external APIs to answer user questions about doctor specialties and appointments.

## Overview

This project implements a hospital chatbot that follows the ReAct (Reason-Act-Observe) paradigm:

1. **Reason**: The agent analyzes user input and determines whether to use a tool or answer directly
2. **Act**: The agent executes actions like calling external APIs when needed
3. **Observe**: The agent processes results from these actions
4. **Final Answer**: The agent formulates a response based on observations

The agent connects to a local LLM (e.g., running on LM Studio) and integrates with Hospital Information System (HIS) APIs for specialties and appointments.

## Features

- ReAct architecture with explicit reasoning, action, and observation steps
- Integration with local LLMs via REST API
- Doctor specialty lookup capability
- Appointment management capabilities
- Web interface for chat interactions
- Extensible tools architecture
- Conversation history tracking

## API Tools

The agent supports multiple API endpoints:

### Specialty APIs
- List all available specialties
- Search specialties by query terms

### Appointment APIs
- Activate SSO
- Search patients by ID number
- Get today's appointments
- View ongoing visits
- Initialize appointments system
- Get user datasets for appointments
- Get appointment session slots
- Create walk-in appointments
- Get appointment numbers
- Create visits
- View patient journey
- Manage follow-up appointments

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- Jinja2
- Requests
- Python-dotenv

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/smartclinicagent.git
cd smartclinicagent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the example environment file and edit it with your configuration:
```bash
cp env.example .env
```

## Configuration

Edit the `.env` file with your specific configuration:

```
# Local LLM Configuration
LLM_ENDPOINT=http://localhost:1234/v1/chat/completions

# API Configuration
SPECIALTY_API_ENDPOINT=http://eserver/api/his/AppointmentsAPI/InitAll
SPECIALTY_API_TOKEN=your_token_here
```

## Usage

Run the FastAPI server to start the web interface:

```bash
python main.py
```

This will start a web server at http://localhost:8000 where you can interact with the chatbot.

Example queries:
- "What specialties are available at your hospital?"
- "Are there any cardiologists in the hospital?"
- "Show me today's appointments"
- "I need to book a walk-in appointment"

## Code Structure

- `react_agent.py`: Main ReAct Agent class implementation following the ReAct paradigm
- `tools.py`: Implementation of all API tools for specialties and appointments
- `main.py`: FastAPI server and web interface
- `requirements.txt`: Python dependencies
- `env.example`: Example environment configuration
- `templates/`: HTML templates for the web interface
- `static/`: Static assets for the web interface

## Extending the Agent

To add new tools/capabilities to the agent:

1. Add a new method to the `Tools` class in `tools.py`
2. Register the tool in the `self.tools` dictionary in the `ReActAgent` class
3. Update the system prompt in `_construct_reasoning_prompt` to include the new tool
4. Add detection methods in `ReActAgent` for identifying when to use your new tool

## License

MIT 