# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Spyfall Online MVP - a social deduction game where one human player competes against AI-powered bot players. The human player must deduce who among them is the spy while the spy tries to identify the location.

## Architecture

**Tech Stack:**
- **Frontend**: React 18+ with TypeScript
- **Backend**: FastAPI with Python 3.9+
- **Real-time Communication**: WebSockets (FastAPI WebSocket support)
- **LLM Integration**: Claude
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
