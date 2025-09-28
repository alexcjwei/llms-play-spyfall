# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Spyfall Online MVP - a social deduction game where one human player competes against AI-powered bot players. The human player must deduce who among them is the spy while the spy tries to identify the location.

## Architecture

**Tech Stack (from spec.md):**
- **Frontend**: React 18+ with TypeScript
- **Backend**: FastAPI with Python 3.9+
- **Real-time Communication**: WebSockets (FastAPI WebSocket support)
- **LLM Integration**: OpenAI API or local LLM (Ollama/LM Studio)
- **State Management**: React Context/useState for client, in-memory for server
- **Styling**: Tailwind CSS

**System Architecture:**
```
┌─────────────────┐    WebSocket    ┌─────────────────┐    HTTP/API    ┌─────────────────┐
│   React Client  │ ←──────────────→ │  FastAPI Server │ ←─────────────→ │   LLM Service   │
│                 │                 │                 │                │                 │
│ - Game UI       │                 │ - Game Logic    │                │ - Question Gen  │
│ - Human Input   │                 │ - Bot Mgmt      │                │ - Answer Gen    │
│ - State Display │                 │ - LLM Requests  │                │ - Strategy AI   │
└─────────────────┘                 └─────────────────┘                └─────────────────┘
```

## Development Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install fastapi uvicorn websockets openai ollama-python
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

**Production Build:**
```bash
# Build React app
npm run build

# Serve with FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Key Components to Implement

### Core Game Logic
- Game room management with WebSocket connections
- Role assignment system (1 spy + location/role for others)
- Turn-based Q&A system with bot AI integration
- Voting and accusation mechanics
- Timer management (8-minute default with countdown)

### LLM Bot System
- Personality-based bot behaviors (Analytical Alice, Casual Bob, Detective Carol, Cautious Dan)
- Strategic question generation and answering based on spy/non-spy roles
- Context-aware responses using game state and Q&A history
- Accusation logic and voting decisions

### UI Components
- Role card display (different styling for spy vs non-spy)
- Real-time Q&A history with turn indicators
- Timer with color-coded warnings (green → yellow → red)
- Player list with bot indicators
- Voting interface for accusations

## Environment Variables

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: False)
- `MAX_GAMES`: Maximum concurrent games (default: 3)
- `LLM_PROVIDER`: 'openai' or 'ollama' (default: openai)
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `LLM_MODEL`: Model name (default: gpt-3.5-turbo for OpenAI, llama2 for Ollama)
- `BOT_RESPONSE_DELAY`: Artificial delay for bot responses in seconds (default: 3)

## Game Content

The game includes 30 locations with 7 roles each. Key examples:
- Airplane: Pilot, Flight Attendant, Passenger, Air Marshal, Mechanic, Tourist, Businessman
- Bank: Teller, Security Guard, Manager, Customer, Robber, Consultant, Armored Car Driver
- Beach: Lifeguard, Surfer, Photographer, Tourist, Ice Cream Vendor, Kite Surfer, Beach Volleyball Player
- Hospital: Doctor, Nurse, Patient, Surgeon, Anesthesiologist, Intern, Therapist

## Development Notes

- This is a local-only MVP (no multiple human players or production deployment)
- Bot responses should have 2-4 second delays to simulate human thinking
- WebSocket events handle real-time game state synchronization
- LLM prompts need careful engineering for spy vs non-spy behavior differentiation
- Game balance is critical - bots should be challenging but not perfect
- Error handling must include LLM service failures with fallback responses

## Testing Requirements

- Unit tests for game logic, bot personalities, and LLM integration
- Integration tests for full game flow with bot players
- Manual testing for user experience and game balance
- Cross-browser compatibility testing

Refer to `spec.md` for complete functional requirements, technical specifications, and implementation details.