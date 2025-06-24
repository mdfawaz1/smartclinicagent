# SmartClinic ReAct Agent

A ReAct (Reason-Act-Observe) agent for a hospital chatbot that interacts with a local LLM and external APIs to answer user questions about doctor specialties.

## Overview

This project implements a hospital chatbot that follows the ReAct (Reason-Act-Observe) paradigm:

1. **Reason**: The agent analyzes user input and determines whether to use a tool or answer directly
2. **Act**: The agent executes actions like calling external APIs when needed
3. **Observe**: The agent processes results from these actions
4. **Final Answer**: The agent formulates a response based on observations

The agent connects to a local LLM (e.g., running on LM Studio) and currently integrates with a Doctor Specialties API.

## Features

- ReAct architecture with explicit reasoning, action, and observation steps
- Integration with local LLMs via REST API
- Doctor specialty lookup capability
- Extensible design for adding new tools/APIs
- Conversation history tracking

## Requirements

- Python 3.8+
- requests
- python-dotenv

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

# Doctor Specialty API Configuration
SPECIALTY_API_ENDPOINT=http://eserver/api/his/AppointmentsAPI/InitAll
SPECIALTY_API_TOKEN=your_token_here
```

## Usage

Run the main script to start the interactive chat demo:

```bash
python main.py
```

Example queries:
- "What specialties are available at your hospital?"
- "Are there any cardiologists in the hospital?"
- "Tell me about the dental department"

## Code Structure

- `react_agent.py`: Main ReAct Agent class implementation
- `main.py`: Demo script and chat interface
- `requirements.txt`: Python dependencies
- `env.example`: Example environment configuration

## Extending the Agent

To add new tools/capabilities to the agent:

1. Add a new method to the `ReActAgent` class for the tool functionality
2. Register the tool in the `self.tools` dictionary in `__init__`
3. Update the system prompt in `_construct_reasoning_prompt` to include the new tool

## License

MIT 