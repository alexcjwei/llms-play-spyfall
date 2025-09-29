# Spyfall Online

A social deduction game where one human player competes against AI-powered bots. The non-spies must identify the spy while the spy tries to guess the secret location.

## Tech Stack

- **Frontend**: React 18 + TypeScript, Tailwind CSS
- **Backend**: FastAPI + Python 3.9+
- **Real-time**: WebSockets
- **AI**: Claude API for intelligent bot behavior

## Quick Start

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

The game will be available at `http://localhost:3000`

## How to Play

1. **Join Game**: Enter your name and join a lobby
2. **Start Game**: Choose number of players (3-8, bots fill remaining slots)
3. **Get Role**: Receive either a location/role card or become the spy
4. **Ask Questions**: Take turns asking questions to identify the spy
5. **Make Accusations**: Vote on who you think is the spy
6. **Win Conditions**:
   - **Non-spies win** if they correctly identify and vote out the spy
   - **Spy wins** if they correctly guess the secret location

## Environment Variables

```bash
# Backend (.env)
CLAUDE_API_KEY=your_claude_key_here
```

## Development Notes

### Known TODOs
- Gather bot votes together asynchronously, not sequentially
- Between each turn, for bots that have not yet accused, prompt to see if they want to accuse a player
