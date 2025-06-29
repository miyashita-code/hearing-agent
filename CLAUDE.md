# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Hearing Agent component of the Re-MENTIA project - an AutoGPT-based system designed to support dementia patients and their caregivers. The agent conducts structured interviews to create procedural manuals for daily living activities (IADLs - Instrumental Activities of Daily Living).

## Development Commands

### Running the Application
```bash
# Development server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --ws websockets

# Production with Gunicorn (as per Procfile)
gunicorn --worker-class eventlet -w 1 app:app
```

### Testing
```bash
# Run tests with pytest
pytest

# Run specific test file
pytest tests/utils/llm/test_llm_chains.py

# Run with coverage
pytest --cov=autogpt_modules
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables (copy .env.example to .env)
cp .env.example .env
```

## Architecture Overview

### Core Components

1. **FastAPI WebSocket Server** (`main.py`)
   - WebSocket endpoint at `/ws/{user_id}`
   - Handles real-time communication with clients
   - Creates AutoGPT instances per room/session

2. **AutoGPT Framework** (`autogpt_modules/core/`)
   - `auto_gpt.py`: Main autonomous agent implementation
   - `room.py`: Session management for each user connection
   - `event_manager.py`: Handles asynchronous events within sessions
   - Uses ReAct (Reasoning + Acting) pattern for agent behavior

3. **Communication Layer** (`autogpt_modules/communication/`)
   - `websocket_manager.py`: Manages WebSocket connections and rooms
   - `message_manager.py`: Handles message queuing and history
   - `plan_manager.py`: Manages multi-step plans
   - `result_manager.py`: Stores and retrieves session results

4. **Tools System** (`autogpt_modules/tools/`)
   - `basic_tools.py`: Core tools (ReplyMessage, Wait, Finish, GoNext)
   - `plan_action.py`: Tool for creating structured plans
   - `save_result.py`: Tool for persisting interview results
   - Tools are decorated with `@tool` decorator for automatic registration

5. **Hearing Module** (`hearing_module/`)
   - `goals.py`: Contains structured interview steps for IADL documentation
   - Defines 5-step process: identify activity → overview → details → follow-up → confirmation

### Key Design Patterns

- **Room-based Architecture**: Each WebSocket connection creates a "room" that encapsulates the session state
- **Event-driven Communication**: Uses event manager for asynchronous coordination
- **Tool-based Actions**: Agent capabilities are modular tools that can be composed
- **Streaming LLM Integration**: Supports streaming responses from OpenAI models

### Important Configuration

- Models are configured in `autogpt_modules/core/custom_congif.py`
- Default model: `gpt-4o-mini-2024-07-18`
- WebSocket timeout: 30 seconds (configurable in `websocket_manager`)

### Message Flow

1. Client connects via WebSocket → Room created
2. Client sends "start_hearing" → AutoGPT instance created with hearing goals
3. Agent processes goals using tools → Sends messages back via WebSocket
4. Client responds → Event manager triggers agent continuation
5. Process continues until "finish" command or completion

### Testing Approach

- Test fixtures in `tests/conftest.py` mock environment variables
- Tests use pytest framework
- Focus on unit testing LLM chains and prompt handling

### Security Considerations

- Environment variables for API keys (never commit .env)
- CORS configured for specific origins in production
- WebSocket connections authenticated by user_id