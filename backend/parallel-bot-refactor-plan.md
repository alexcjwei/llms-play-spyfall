# Parallel Bot Infrastructure Refactor Plan

## Overview
Refactor from sequential, turn-based bot prompting to parallel, tool-based bot querying where all bots are queried simultaneously after each turn with different tool options based on game state.

## Current System vs New System

### Current (Sequential)
- Only the "current turn" bot acts
- Separate prompt-based methods for questions, answers, voting
- One bot action per turn cycle

### New (Parallel)
- ALL bots queried after every Q&A or mid-game accusation
- Tool-based system with dynamic tool availability
- Multiple bots can act simultaneously (with conflict resolution)

## Design Requirements Summary

### Tool Availability by Game State
1. **Bot's turn to ask**: `[ask_tool, accuse_tool, guess_location_tool]` (if spy)
2. **Bot's turn to answer**: `[answer_tool, accuse_tool, guess_location_tool]` (if spy)
3. **Not bot's turn**: `[guess_location_tool]` (if spy) + `[accuse_tool]` (if haven't accused this round)

### Key Behaviors
- Query all bots after each Q&A exchange or mid-game accusation
- Process multiple tool calls per bot in order: `[guess_location, ask, answer, accuse]`
- If multiple bots accuse simultaneously, process the first one only
- Use `tool_choice: "required"` to force tool usage
- Simple fallback responses for LLM failures (no complex retry logic)

## Implementation Plan

### Phase 1: Tool Schema & Handlers
**File: `backend/tools/game_actions.py`**

1. **Fix Tool Schemas**
   - Fix `accuse_tool.target` to be optional string (empty = no accusation)
   - Complete `guess_location_tool` with full location enum from game data
   - Ensure all schemas have proper validation

2. **Implement Tool Handler Functions**
   ```python
   def ask(game: Game, bot_id: str, thought: str, question: str, target: str) -> bool
   def answer(game: Game, bot_id: str, thought: str, answer: str) -> bool
   def accuse(game: Game, bot_id: str, thought: str, target: str = "") -> bool
   def guess_location(game: Game, bot_id: str, thought: str, location: str) -> bool
   ```
   - Integrate with existing game logic (game.ask_question, game.give_answer, etc.)
   - Add validation (can't ask person who just asked you, etc.)
   - Log thoughts for debugging/analysis

### Phase 2: Tool Selection Logic
**File: `backend/services/tool_selector.py` (new)**

Create service to determine available tools for each bot based on:
- Current game state (whose turn, waiting for answer, etc.)
- Bot role (spy vs non-spy)
- Bot accusation history this round
- Game status (IN_PROGRESS, VOTING, etc.)

```python
def get_available_tools(game: Game, bot_id: str) -> List[Dict]
```

### Phase 3: Parallel Bot Query System
**File: `backend/services/parallel_bot_service.py` (new)**

1. **Core Parallel Query Function**
   ```python
   async def query_all_bots(game: Game) -> Dict[str, Any]:
       # Get available tools for each bot
       # Create parallel LLM requests with asyncio.gather
       # Process responses and extract tool calls
       # Return structured results for processing
   ```

2. **Tool Call Processing**
   ```python
   async def process_bot_responses(game: Game, responses: Dict) -> GameUpdateResult:
       # Process tool calls in priority order: [guess_location, ask, answer, accuse]
       # Handle conflicts (multiple accusations = take first)
       # Apply valid actions to game state
       # Return summary of changes
   ```

### Phase 4: LLM Service Updates
**File: `backend/services/llm_service.py`**

1. **Add Tool-Based Request Method**
   ```python
   async def query_bot_with_tools(
       game_state: Dict,
       bot_id: str,
       available_tools: List[Dict],
       prompt_builder: Callable
   ) -> Optional[Dict]:
       # Use tool_choice: "required"
       # Parse tool call responses
       # Handle LLM failures with simple fallbacks
   ```

2. **Update Prompt Builder Integration**
   - Extend existing prompt builders to support tool-based calls
   - Include available tools in prompt context
   - Maintain existing bot personality system

### Phase 5: Bot Orchestrator Refactor
**File: `backend/utils/bot_orchestrator.py`**

1. **Replace Sequential Logic**
   - Remove existing turn-based scheduling
   - Implement parallel bot querying after each turn
   - Trigger on: Q&A completion, mid-game accusations

2. **New Orchestration Flow**
   ```python
   async def handle_post_turn_actions(game: Game):
       # Query all bots in parallel
       # Process responses and update game state
       # Send updated game state to clients
       # Schedule next human turn or handle game end conditions
   ```

### Phase 6: Integration & Cleanup
**Files: `backend/services/bot_service.py`, `backend/main.py`**

1. **Update Bot Service**
   - Replace existing methods with new parallel system
   - Maintain existing error handling patterns
   - Keep fallback logic simple

2. **Update Main Application**
   - Wire up new services and dependencies
   - Update WebSocket event handling for parallel responses
   - Ensure proper cleanup of async tasks

### Phase 7: Testing & Validation

1. **Unit Tests**
   - Tool handler functions
   - Tool selection logic
   - Parallel query processing

2. **Integration Tests**
   - Full game flow with parallel bot actions
   - Conflict resolution (multiple accusations)
   - Game state consistency

3. **Performance Testing**
   - Parallel LLM request latency
   - Memory usage with multiple concurrent requests

## Technical Considerations

### Tool Call Priority Order
1. `guess_location` - Ends game immediately if spy guesses correctly
2. `ask` - Advances game turn
3. `answer` - Completes current Q&A exchange
4. `accuse` - Stops timer and forces voting (only process first one)

### Error Handling Strategy
- LLM request failures: Use simple fallback responses (like current system)
- Invalid tool calls: Log and ignore (don't retry)
- Tool conflicts: Process in priority order, ignore later conflicting calls

### Game State Synchronization
- Apply all valid tool calls atomically
- Send single game state update after processing all bot responses
- Ensure WebSocket clients receive consistent state

## Migration Strategy

1. Keep existing bot system running during development
2. Add feature flag to switch between old/new systems
3. Test new system thoroughly in parallel
4. Cut over when stable and validated
5. Remove old system code after successful migration

## Success Criteria

- All bots participate after each turn (not just current player)
- Game flow maintains proper timing and turn progression
- Bot personalities and strategic behaviors preserved
- No performance degradation from parallel requests
- Conflict resolution works correctly for simultaneous actions
- Existing game balance and user experience maintained