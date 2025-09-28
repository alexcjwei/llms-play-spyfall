# Spyfall Online MVP - Requirements & Design Document

## 1. Project Overview

### 1.1 Purpose
Create a simplified, locally-hosted web application for playing Spyfall against AI opponents - a social deduction game where players deduce who among them is the spy while the spy tries to identify their location. The human player competes against configurable LLM-powered bot players.

### 1.2 Scope
**MVP Features:**
- Single game session (no multiple rounds)
- 1 human player + 2-7 configurable LLM bot players
- Turn-based Q&A system with AI-generated responses
- Real-time game state synchronization
- Built-in timer and voting system
- Local deployment only

**Explicitly Out of Scope:**
- Multiple human players
- User accounts or authentication
- Multiple concurrent games
- Live chat/messaging
- Voice chat
- Game persistence/history
- Mobile optimization
- Production deployment features

## 2. Functional Requirements

### 2.1 Game Setup (FR-1)

**FR-1.1 Game Creation**
- Human player creates a new game
- System generates unique 6-character room code for reference
- Player configures number of bot opponents (2-7 bots)
- Player can configure game duration (6, 8, 10, or 12 minutes)
- Total players: 1 human + 2-7 bots = 3-8 total players

**FR-1.2 Bot Generation**
- System creates specified number of bot players with random names
- Bot players are clearly marked as "Bot" in the player list
- Each bot has a distinct personality/questioning style
- Human player can start game immediately (no waiting for others to join)

**FR-1.3 Role Assignment**
- System randomly selects 1 location from 30 available locations
- System randomly assigns 1 player (human or bot) as spy
- Non-spy players receive location + specific role
- Assignment happens when human player starts the game

### 2.2 Game Flow (FR-2)

**FR-2.1 Game State Management**
- Game progresses through phases: Setup → Playing → Voting → Results
- Timer starts automatically when game begins
- All players see current game phase and remaining time
- Game state synchronizes in real-time across all clients

**FR-2.2 Information Display**
- Each player sees their own role card clearly
- Spy sees: "SPY" only
- Non-spies see: Location name + specific role
- All players see: player list, timer, current phase
- Non-spies can access complete location reference list

**FR-2.3 Turn Management**
- Structured turn order starting with human player
- Current player asks a question to any other player (human or bot)
- If human answers: they become next questioner
- If bot answers: they automatically become next questioner
- Cannot ask question back to the person who just asked you
- Turn indicator shows whose turn it is to ask a question
- Human or any bot can initiate accusations during any turn

### 2.3 Question & Answer System (FR-3)

**FR-3.1 Turn Structure**
- Human player asks questions via text input field
- Bot players generate questions using LLM prompting
- Questions are displayed to all players with clear sender/recipient labels
- Human answers are typed in response field
- Bot answers are generated automatically using LLM
- After answering, that player becomes the next questioner

**FR-3.2 Turn Flow Management**
- Visual indicator shows whose turn it is to ask a question
- Human player selects target from dropdown of other players
- Bot players automatically select targets using strategic logic
- Cannot select the player who just asked you a question
- System enforces turn order and restrictions
- Turn automatically advances after each Q&A exchange

**FR-3.3 Q&A Display**
- Chronological list of all questions and answers
- Clear formatting: "Player A asks Player B: [Question]"
- Followed by: "Player B responds: [Answer]"
- Bot players clearly marked as "Bot" in all exchanges
- Auto-scroll to newest Q&A exchange
- Question/answer character limits (200 chars each)

### 2.4 LLM Bot Behavior (FR-4)

**FR-4.1 Bot Question Generation**
- Bots generate contextual questions based on their role and location knowledge
- Spy bots ask probing questions to deduce the location
- Non-spy bots ask questions that subtly confirm location knowledge
- Questions should sound natural and human-like
- Bot questions vary in style/personality per bot

**FR-4.2 Bot Answer Generation**
- Bots provide contextually appropriate answers based on their assigned role
- Spy bots give vague or misdirecting answers to avoid detection
- Non-spy bots give specific but not too obvious location-related answers
- Answers demonstrate role knowledge without being too explicit
- Response time: 2-4 second delay to simulate thinking

**FR-4.3 Bot Accusation Logic**
- Bots can strategically make accusations based on Q&A analysis
- Spy bots may make false accusations to deflect suspicion
- Non-spy bots analyze answer patterns to identify potential spy
- Accusation frequency: moderate (not too aggressive)
- Bots participate in voting when accusations are made

**FR-4.4 Bot Strategic Behavior**
- Each bot has a difficulty level affecting question/answer sophistication
- Bots should make occasional "mistakes" to seem human-like
- Spy bots attempt location guessing when confident
- Non-spy bots try to coordinate suspicions through questioning patterns

### 2.5 Accusation & Voting System (FR-5)

**FR-5.1 Making Accusations**
- Human player can click "Accuse Player" button during play phase
- Bot players can strategically make accusations based on game analysis
- Accuser selects target from dropdown list
- Accusation immediately pauses game timer
- System announces accusation to all players

**FR-5.2 Voting Process**
- All players except accused can vote (Yes/No)
- Human uses voting interface buttons
- Bots automatically vote based on their analysis and strategy
- Voting interface shows accused player clearly
- Real-time vote tallies visible to human player
- 30-second voting timer with visual countdown
- Majority vote required (>50% of eligible voters)

**FR-5.3 Vote Resolution**
- If vote passes: accused player's card is revealed to all
- If vote fails: game timer resumes, accuser cannot accuse again
- Win/loss determination happens immediately after card reveal

### 2.6 Spy Guess Feature (FR-6)

**FR-6.1 Location Guessing**
- Human spy can click "Guess Location" button anytime during play phase
- Bot spy can strategically guess location when confident enough
- Guesser selects from dropdown of all 30 locations
- Guess immediately ends game
- Win/loss determination based on correct/incorrect guess

### 2.7 End Game Conditions (FR-7)

**FR-7.1 Game Ending Triggers**
- Timer expires (8 minutes default)
- Successful accusation vote
- Human or bot spy makes location guess
- Human player manually ends game

**FR-7.2 End-of-Round Voting (Timer Expiry)**
- When timer reaches 0:00, automatic voting phase begins
- Each player gets one accusation (starting with human, then bots in order)
- Same voting mechanics as mid-game accusations
- Bots make strategic accusations during this phase
- If no unanimous decision after all players accuse, spy wins
- 60-second timer per accusation round

**FR-7.3 Results Display**
- Clear win/loss announcement for human player
- All player cards revealed (including bot roles)
- Correct location displayed
- Option to start new game with different bot configuration

## 3. Technical Requirements

### 3.1 Architecture (TR-1)

**TR-1.1 Tech Stack**
- **Frontend**: React 18+ with TypeScript
- **Backend**: FastAPI with Python 3.9+
- **Real-time Communication**: WebSockets (FastAPI WebSocket support)
- **LLM Integration**: OpenAI API or local LLM (Ollama/LM Studio)
- **State Management**: React Context/useState for client, in-memory for server
- **Styling**: Tailwind CSS

**TR-1.2 System Architecture**
```
┌─────────────────┐    WebSocket    ┌─────────────────┐    HTTP/API    ┌─────────────────┐
│   React Client  │ ←──────────────→ │  FastAPI Server │ ←─────────────→ │   LLM Service   │
│                 │                 │                 │                │                 │
│ - Game UI       │                 │ - Game Logic    │                │ - Question Gen  │
│ - Human Input   │                 │ - Bot Mgmt      │                │ - Answer Gen    │
│ - State Display │                 │ - LLM Requests  │                │ - Strategy AI   │
└─────────────────┘                 └─────────────────┘                └─────────────────┘
```

### 3.2 Data Models (TR-2)

**TR-2.1 Core Data Structures**
```typescript
interface Player {
  id: string;
  name: string;
  isHost: boolean;
  isConnected: boolean;
}

interface GameRoom {
  roomCode: string;
  players: Player[];
  gameState: GameState;
  config: GameConfig;
}

interface GameState {
  phase: 'setup' | 'playing' | 'voting' | 'ended';
  location: string | null;
  spyId: string | null;
  playerRoles: Map<string, PlayerRole>;
  timer: {
    duration: number;
    remaining: number;
    isRunning: boolean;
  };
  currentVote?: VotingState;
}

interface VotingState {
  accuserId: string;
  accusedId: string;
  votes: Map<string, boolean>;
  timeRemaining: number;
}
```

### 3.3 API Specifications (TR-3)

**TR-3.1 HTTP Endpoints**
```
POST /api/games          - Create new game with bot configuration
GET  /api/games/{code}   - Get game info
POST /api/games/{code}/start - Start game (triggers role assignment)
```

**TR-3.2 WebSocket Events**
```typescript
// Client → Server (Human Player Only)
interface WSClientEvents {
  'join-game': { gameCode: string; playerName: string };
  'start-game': { numBots: number };
  'ask-question': { targetId: string; question: string };
  'answer-question': { answer: string };
  'make-accusation': { accusedPlayerId: string };
  'cast-vote': { vote: boolean };
  'spy-guess': { locationGuess: string };
}

// Server → Client  
interface WSServerEvents {
  'game-updated': { game: GameRoom };
  'game-started': { playerRole: PlayerRole };
  'question-asked': { qaExchange: QAExchange };
  'answer-given': { qaExchange: QAExchange };
  'turn-changed': { currentTurnPlayerId: string };
  'bot-thinking': { botId: string; action: 'questioning' | 'answering' };
  'accusation-made': { accusation: AccusationEvent };
  'vote-cast': { votingState: VotingState };
  'game-ended': { result: GameResult };
  'error': { message: string };
}
```

**TR-3.3 LLM Integration API**
```typescript
interface LLMService {
  generateQuestion(request: LLMRequest): Promise<string>;
  generateAnswer(request: LLMRequest): Promise<string>;
  makeAccusationDecision(request: LLMRequest): Promise<boolean>;
  selectAccusationTarget(request: LLMRequest): Promise<string>;
  castVote(request: LLMRequest): Promise<boolean>;
  guessLocation(request: LLMRequest): Promise<string>;
}
```
```

### 3.4 Performance Requirements (TR-4)

**TR-4.1 Response Times**
- WebSocket message latency: <100ms on local network
- Game state updates: <200ms propagation to all clients
- Timer accuracy: ±1 second tolerance

**TR-4.2 Capacity**
- Support up to 3 concurrent games
- Maximum 1 human + 7 bots per game
- Handle up to 10 total concurrent connections

## 4. User Interface Design

### 4.1 Layout Structure (UI-1)

**UI-1.1 Main Game Screen Layout**
```
┌─────────────────────────────────────────────────────┐
│                    Header Bar                        │
│  Game: ABC123  |  Players: 1+4 Bots  |  Timer: 07:23│
├─────────────────┬───────────────────────────────────┤
│                 │                                   │
│   Player List   │           Game Area               │
│                 │                                   │
│ • You           │  ┌─────────────────────────────┐   │
│ • Alice (Bot) ← │  │       Your Role Card        │   │
│ • Bob (Bot)     │  │                             │   │
│ • Carol (Bot)   │  │      🏦 BANK                │   │
│ • Dan (Bot)     │  │      Security Guard         │   │
│                 │  └─────────────────────────────┘   │
│                 │                                   │
│ [Accuse Player] │  Turn Status: "Alice is thinking..."│
│ [View Locations]│  Ask: [Dropdown] [Question Input] │
│                 │  [Guess Location] (spy only)      │
│                 │  [End Game]                       │
├─────────────────┴───────────────────────────────────┤
│                 Q&A History                         │
│  You ask Alice: "Do you like working here?"         │
│  Alice (Bot) responds: "Yes, the customers are nice"│
│  Alice asks Bob: "How long have you worked here?"   │
│  Bob (Bot) responds: "About 2 years now"           │
│  > Bob's turn to ask a question                     │
└─────────────────────────────────────────────────────┘
```

### 4.2 Component Specifications (UI-2)

**UI-2.1 Role Card Component**
- Prominent display of player's role information
- Different styling for spy vs. non-spy cards
- Always visible during game play
- Responsive design for different screen sizes

**UI-2.2 Timer Component**
- Large, easily readable countdown
- Color changes: Green (>3 min) → Yellow (1-3 min) → Red (<1 min)
- Visual progress bar
- Audio alert at 1 minute remaining

**UI-2.3 Q&A History Component**
- Chronological display of all questions and answers
- Clear visual separation between Q&A pairs
- Auto-scrolling to newest exchange
- Different styling for questions vs answers
- Turn indicator showing whose turn is next

**UI-2.5 Turn Management Interface**
- Clear indication of whose turn it is to ask a question
- Dropdown to select question target (excludes previous questioner)
- Text input for typing questions
- Text input for answers (only visible when it's your turn to answer)
- Visual feedback for sent questions/answers
**UI-2.7 Bot Status Indicators**
- Clear "(Bot)" labels in player list and Q&A history
- "Bot is thinking..." status messages during response generation
- Visual differentiation between human and bot players
- Bot response timing indicators (2-4 second delays)
**UI-2.8 Voting Interface**
- Modal overlay during voting
- Clear display of accused player
- Yes/No buttons for human player
- Real-time vote tally including bot votes
- Countdown timer for voting phase

### 4.3 User Experience Flow (UI-3)

**UI-3.1 Player Journey**
1. Create game → Configure number of bots → Start game
2. Game starts → View role card → Wait for turn or answer questions
3. Ask questions on your turn → Observe bot behavior → Make/respond to accusations
4. Vote on accusations → See results → New game option

**UI-3.2 Error Handling**
- Connection lost: Show reconnection status
- LLM service unavailable: Inform player and suggest retry
- Bot response timeout: Skip bot turn and continue
- Invalid game configuration: Clear error message with suggestions name

## 5. LLM Integration Requirements

### 5.1 LLM Service Configuration (LLM-1)

**LLM-1.1 Service Options**
- **Primary**: OpenAI GPT-4 or GPT-3.5-turbo via API
- **Alternative**: Local LLM via Ollama (llama2, mistral, etc.)
- **Fallback**: Simple rule-based responses for offline mode
- Configurable LLM endpoint in environment variables

**LLM-1.2 Prompt Engineering**
- Separate prompt templates for spy vs non-spy behaviors
- Context-aware prompts including Q&A history and game state
- Personality-based prompt variations for different bot styles
- Response format constraints (character limits, natural language)

**LLM-1.3 Response Handling**
- 10-second timeout for LLM API calls
- Retry logic for failed requests (3 attempts)
- Fallback to simpler responses if LLM unavailable
- Response validation and sanitization

### 5.2 Bot Personality System (LLM-2)

**LLM-2.1 Personality Types**
```typescript
const BOT_PERSONALITIES = {
  'Analytical Alice': {
    questioningStyle: 'analytical',
    suspicionLevel: 'high',
    rolePlayingIntensity: 'moderate',
    traits: ['methodical', 'detail-oriented', 'logical']
  },
  'Casual Bob': {
    questioningStyle: 'casual',
    suspicionLevel: 'low',
    rolePlayingIntensity: 'subtle',
    traits: ['laid-back', 'friendly', 'trusting']
  },
  'Detective Carol': {
    questioningStyle: 'aggressive',
    suspicionLevel: 'high',
    rolePlayingIntensity: 'obvious',
    traits: ['suspicious', 'direct', 'accusatory']
  },
  'Cautious Dan': {
    questioningStyle: 'cautious',
    suspicionLevel: 'medium',
    rolePlayingIntensity: 'subtle',
    traits: ['careful', 'observant', 'hesitant']
  }
};
```

**LLM-2.2 Behavioral Consistency**
- Each bot maintains consistent personality throughout game
- Question/answer style reflects personality traits
- Accusation frequency varies by suspicion level
- Role-playing intensity affects location knowledge display

### 5.3 Game Strategy Implementation (LLM-3)

**LLM-3.1 Spy Bot Strategy**
- Ask broad questions that could apply to multiple locations
- Give vague answers that don't reveal lack of location knowledge
- Analyze Q&A patterns to deduce the location
- Make strategic false accusations to deflect suspicion
- Guess location when confidence threshold reached (70%+)

**LLM-3.2 Non-Spy Bot Strategy**
- Ask location-specific questions without being too obvious
- Give role-appropriate answers that demonstrate location knowledge
- Identify suspicious behavior patterns in other players
- Coordinate suspicions through strategic questioning
- Vote based on accumulated evidence from Q&A exchanges

**LLM-3.3 Difficulty Scaling**
- **Easy**: Bots make more obvious mistakes, less strategic thinking
- **Medium**: Balanced gameplay with occasional suboptimal moves
- **Hard**: Sophisticated strategy, minimal mistakes, advanced deduction

## 6. Game Content

### 6.1 Locations & Roles (GC-1)

**GC-1.1 Location Set (30 locations)**
```
1. Airplane - Pilot, Flight Attendant, Passenger, Air Marshal, Mechanic, Tourist, Businessman
2. Bank - Teller, Security Guard, Manager, Customer, Robber, Consultant, Armored Car Driver  
3. Beach - Lifeguard, Surfer, Photographer, Tourist, Ice Cream Vendor, Kite Surfer, Beach Volleyball Player
4. Casino - Dealer, Gambler, Bartender, Security, VIP, Slot Attendant, Pit Boss
5. Hospital - Doctor, Nurse, Patient, Surgeon, Anesthesiologist, Intern, Therapist
... (complete list of 30 locations with 7 roles each)
```

### 6.2 Game Balance (GC-2)

**GC-2.1 Timing**
- Default 8-minute timer provides optimal tension
- 30-second voting windows prevent stalling
- 1-minute warning creates urgency
- Bot response delays (2-4 seconds) simulate human thinking

**GC-2.2 Role Distribution**
- Each location has 7 distinct roles
- Roles are specific enough to enable role-playing
- Roles avoid gender-specific language where possible
- Bot personalities complement different role types

## 7. Implementation Plan

### 7.1 Development Phases (IP-1)

**Phase 1: Core Infrastructure (Week 1)**
- Basic FastAPI server setup
- WebSocket connection handling
- Game creation and basic state management
- Basic React UI framework with game setup

**Phase 2: Game Logic & Bots (Week 2)**
- Role assignment system
- Timer implementation
- Bot player generation and management
- LLM service integration and basic prompting

**Phase 3: Q&A System (Week 3)**
- Turn-based question/answer system
- Real-time state synchronization
- Bot question/answer generation
- Accusation system and voting mechanics

**Phase 4: Polish & Testing (Week 4)**
- UI improvements and bot status indicators
- Error handling and fallback responses
- End-to-end testing with bot interactions
- Performance optimization and LLM response caching

### 7.2 Testing Strategy (IP-2)

**Unit Tests**
- Game logic functions
- Bot personality and strategy systems
- LLM prompt generation and response parsing
- WebSocket event handlers

**Integration Tests**
- Full game flow with bot players
- LLM service integration
- Human-bot interaction scenarios
- Connection handling and error recovery

**Manual Testing**
- User experience testing against different bot personalities
- LLM response quality and consistency
- Game balance and difficulty scaling
- Cross-browser compatibility

## 8. Deployment

### 8.1 Local Development (DP-1)

**Development Setup**
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn websockets openai ollama-python
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend  
cd frontend
npm install
npm start
```

**Production Build**
```bash
# Build React app
npm run build

# Serve with FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 8.2 Configuration (DP-2)

**Environment Variables**
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: False)
- `MAX_GAMES`: Maximum concurrent games (default: 3)
- `LLM_PROVIDER`: 'openai' or 'ollama' (default: openai)
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `LLM_MODEL`: Model name (default: gpt-3.5-turbo for OpenAI, llama2 for Ollama)
- `BOT_RESPONSE_DELAY`: Artificial delay for bot responses in seconds (default: 3)

## 9. Future Considerations

### 9.1 Potential Enhancements
- Multiple rounds with scoring against bot teams
- Custom location sets and user-created content
- Advanced bot difficulty settings and learning
- Multiplayer mode (human + bots vs other human + bots)
- Voice synthesis for bot responses
- Analytics on bot performance and human win rates

### 9.2 Scalability Notes
- Current design supports local single-player usage
- Database integration needed for bot behavior learning
- Consider fine-tuning custom models for better bot performance
- Caching strategies for LLM responses to reduce API costs
- Bot behavior analysis for continuous improvement

### 9.3 LLM Considerations
- Monitor API costs for OpenAI usage
- Implement response caching for common scenarios
- Consider local LLM deployment for offline play
- Fine-tune prompts based on gameplay analytics
- Develop fallback rule-based system for LLM failures

---

**Document Version**: 1.0  
**Last Updated**: [Current Date]  
**Status**: Ready for Implementation
