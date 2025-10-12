# Message History Implementation Plan

## Overview
Implement persistent message history for each bot to enable:
- Multi-turn conversations with Claude API
- Prompt caching support (future)
- Better bot reasoning with access to previous thoughts
- Reduced redundant context in each API call

## Current State
- Messages are sent to each bot multiple times during a round
- Each API call only sees one user message (reformatted game state)
- Bots don't have access to previous thoughts or responses
- No conversation history preserved between queries

## Target Architecture

### Message Flow
1. **System message**: "You are an AI agent playing the social deduction game Spyfall."
2. **First user message**: Spyfall background + role card + initial players + instruction
3. **Bot response**: Assistant message with tool_use blocks
4. **Tool results**: User message with tool_result blocks
5. **Next query**: User message with new game events + next instruction
6. **Repeat**: Assistant response → tool results → new events → ...

### Message History Structure
```python
bot_message_histories = {
    bot_id: {
        "system": "You are an AI agent playing...",
        "messages": [
            {"role": "user", "content": [...]},
            {"role": "assistant", "content": [...]},
            {"role": "user", "content": [...]},
            ...
        ],
        "last_seen_event_index": int
    }
}
```

## Implementation Phases

### Phase 1: GameEvent System

**Goal**: Replace `Game.messages` with an append-only event log

#### 1.1 Create GameEvent dataclass (`models/message.py`)
```python
@dataclass
class GameEvent:
    type: str  # "question", "answer", "accusation", "vote", etc.
    player_id: str
    content: Dict[str, Any]  # event-specific data (target, text, etc.)
    timestamp: float
    formatted_text: str  # pre-formatted for bot consumption
```

**Event Types to Support**:
- `question`: {"to_id": str, "text": str}
- `answer`: {"to_id": str, "text": str}
- `accusation`: {"accused_id": str}
- `vote`: {"accusation_id": str, "vote": bool}
- `accusation_resolved`: {"result": str, "reason": str}
- `spy_guess_location`: {"guess": str, "correct": bool}
- `round_end`: {"reason": str}
- `game_end`: {"winner": str, "reason": str}

#### 1.2 Update Game model (`models/game.py`)
- Replace `messages: List[Message]` with `events: List[GameEvent]`
- Remove `Message`, `Accusation` dataclasses (replace with events)
- Update all methods that create messages to create events instead:
  - `ask_question()` → creates "question" event
  - `give_answer()` → creates "answer" event
  - `stop_clock_for_accusation()` → creates "accusation" event
  - `vote_on_accusation()` → creates "vote" event
  - `_resolve_accusation()` → creates "accusation_resolved" event
  - `spy_guess_location()` → creates "spy_guess_location" event
  - etc.

#### 1.3 Event formatting helper
Create `format_event(event: GameEvent) -> str` that formats based on type:
```python
def format_event(event: GameEvent) -> str:
    if event.type == "question":
        from_name = get_player_name(event.player_id)
        to_name = get_player_name(event.content["to_id"])
        return f"{from_name} asked {to_name}: \"{event.content['text']}\""
    # ... other types
```

Actually, store formatted_text in event on creation.

#### 1.4 Migration tasks
- Update all code reading `game.messages` to use `game.events`
- Update `tool_prompt_builder.py` to use events
- Update `game.to_dict()` to serialize events
- Update frontend to consume events instead of messages
- Update tests

### Phase 2: Bot Message History Service

**Goal**: Create centralized bot message history management

#### 2.1 Create `services/bot_message_history.py`
```python
from typing import Dict, List, Any

# Global storage
bot_message_histories: Dict[str, Dict[str, Any]] = {}

SYSTEM_PROMPT = "You are an AI agent playing the social deduction game Spyfall."

def initialize_bot_history(bot_id: str, initial_message: Dict[str, Any]):
    """Initialize message history for a bot"""
    bot_message_histories[bot_id] = {
        "system": SYSTEM_PROMPT,
        "messages": [initial_message],
        "last_seen_event_index": 0
    }

def get_bot_history(bot_id: str) -> Dict[str, Any]:
    """Get bot's message history"""
    return bot_message_histories.get(bot_id)

def append_assistant_message(bot_id: str, content: List[Dict]):
    """Append assistant's response to history"""
    bot_message_histories[bot_id]["messages"].append({
        "role": "assistant",
        "content": content
    })

def append_user_message(bot_id: str, content: List[Dict]):
    """Append user message to history"""
    bot_message_histories[bot_id]["messages"].append({
        "role": "user",
        "content": content
    })

def update_last_seen_event_index(bot_id: str, index: int):
    """Update the last seen event index"""
    bot_message_histories[bot_id]["last_seen_event_index"] = index

def clear_all_histories():
    """Clear all bot histories (for testing)"""
    bot_message_histories.clear()
```

### Phase 3: LLM Service Updates

**Goal**: Support full message history and extract tool IDs

#### 3.1 Update `llm_service.query_bot_with_tools()` signature
```python
async def query_bot_with_tools(
    self,
    messages: List[Dict[str, Any]],  # Full message history
    bot_id: str,
    available_tools: List[Dict[str, Any]],
    system: str,  # System prompt
    max_tokens: int = 1024,
    temperature: float = 0.7
) -> Optional[Dict[str, Any]]:
```

#### 3.2 Update API request payload
```python
payload = {
    "model": self.model,
    "max_tokens": max_tokens,
    "temperature": temperature,
    "system": system,  # Add system prompt
    "messages": messages,  # Use full message history
    "tools": available_tools,
    "tool_choice": {"type": "any"}
}
```

#### 3.3 Extract tool IDs from response
```python
tool_calls = []
for item in content:
    if item.get("type") == "tool_use":
        tool_calls.append({
            "id": item.get("id"),  # Extract ID
            "name": item.get("name"),
            "parameters": item.get("input", {})
        })
```

#### 3.4 Return full response content
```python
return {
    "tool_calls": tool_calls,
    "response_content": content  # Full content array
}
```

### Phase 4: Parallel Bot Service Updates

**Goal**: Integrate message history into bot querying flow

#### 4.1 Update BotResponse dataclass
```python
@dataclass
class BotResponse:
    bot_id: str
    tool_calls: List[Dict[str, Any]]  # Now includes 'id'
    response_content: List[Dict]  # Full content array
    success: bool
    error: Optional[str] = None
```

#### 4.2 Update `_query_single_bot()`

**First query flow** (bot has no history):
1. Get available tools
2. Build initial user message content:
   - Spyfall background (locations, rules, etc.)
   - Role card (location + role for bot)
   - Player list
   - Initial instruction (from `get_action_context()`)
3. Initialize bot history with this message
4. Set `last_seen_event_index = len(game.events)`

**Subsequent query flow** (bot has history):
1. Get bot history
2. Get new events: `game.events[last_seen_event_index:]`
3. Format events as text
4. Get current instruction
5. Append user message with events + instruction

**Common flow**:
1. Query API with full message history
2. Extract tool calls with IDs
3. Return BotResponse with response_content

```python
async def _query_single_bot(self, game: Game, bot_id: str) -> BotResponse:
    try:
        available_tools = tool_selector.get_available_tools(game, bot_id)
        if not available_tools:
            return BotResponse(bot_id=bot_id, tool_calls=[], response_content=[], success=True)

        # Get or initialize bot history
        bot_history = get_bot_history(bot_id)

        if not bot_history:
            # First query - build initial message
            initial_content = self._build_initial_message_content(game, bot_id)
            initialize_bot_history(bot_id, {"role": "user", "content": initial_content})
            update_last_seen_event_index(bot_id, len(game.events))
            bot_history = get_bot_history(bot_id)
        else:
            # Subsequent query - append new events and instruction
            last_index = bot_history["last_seen_event_index"]
            new_events = game.events[last_index:]

            if new_events:
                events_text = self._format_events(new_events, game)
                instruction = get_action_context(game, bot_id)

                user_content = events_text + f"\n\n{instruction}"
                append_user_message(bot_id, user_content)

        # Query with full history
        response = await self.llm_service.query_bot_with_tools(
            messages=bot_history["messages"],
            bot_id=bot_id,
            available_tools=available_tools,
            system=bot_history["system"]
        )

        if response and response.get('tool_calls'):
            return BotResponse(
                bot_id=bot_id,
                tool_calls=response['tool_calls'],
                response_content=response['response_content'],
                success=True
            )
        else:
            return BotResponse(bot_id=bot_id, tool_calls=[], response_content=[], success=True)

    except Exception as e:
        logger.error(f"Error querying bot {bot_id}: {e}")
        return BotResponse(bot_id=bot_id, tool_calls=[], response_content=[], success=False, error=str(e))
```

#### 4.3 Update `process_bot_responses()`

After executing all tools, update message histories:

```python
async def process_bot_responses(self, game: Game, responses: List[BotResponse]) -> GameUpdateResult:
    # ... existing tool execution logic ...

    # After all tools executed, update message histories
    for response in responses:
        if not response.success or not response.response_content:
            continue

        # Append assistant message (bot's response with tool use)
        append_assistant_message(response.bot_id, response.response_content)

        # Build tool results
        tool_results = []
        for tool_call in response.tool_calls:
            tool_id = tool_call.get('id')
            success, error = tool_execution_results.get((response.bot_id, tool_id), (True, None))

            result_content = "success" if success else f"error: {error}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_content
            })

        # Append user message with tool results
        append_user_message(response.bot_id, tool_results)

        # Update last seen event index
        update_last_seen_event_index(response.bot_id, len(game.events))

    return GameUpdateResult(actions_taken, errors, game_ended, accusation_made)
```

#### 4.4 Helper methods
```python
def _build_initial_message_content(self, game: Game, bot_id: str) -> str:
    """Build the first user message for a bot"""
    # Background + role + players + instruction
    # (Use existing build_bot_tool_prompt logic)

def _format_events(self, events: List[GameEvent], game: Game) -> str:
    """Format events for bot consumption"""
    if not events:
        return "No new events since your last turn."

    formatted = ["Recent game events:"]
    for event in events:
        formatted.append(f"- {event.formatted_text}")

    return "\n".join(formatted)
```

### Phase 5: Cleanup

#### 5.1 Remove deprecated methods from `llm_service.py`
- `generate_question()`
- `generate_answer()`
- `should_make_accusation()`
- `should_vote_guilty()`
- `extract_xml_tags()`
- `get_xml_completion()`

#### 5.2 Update/remove `tool_prompt_builder.py`
- Keep `get_action_context()`
- Simplify `build_bot_tool_prompt()` to just build initial content
- Remove redundant prompt building logic

#### 5.3 Update tests
- `test_llm_tools.py`: Update for new message history approach
- `test_parallel_bot_service.py`: Update for GameEvent system
- `test_llm_integration.py`: Update integration tests
- `test_tool_integration.py`: Update tool integration tests

#### 5.4 Update WebSocket handlers
- Update game state serialization to use events
- Ensure frontend receives properly formatted events

#### 5.5 Remove unused code
- Old Message/Accusation handling if fully replaced
- Any other deprecated utility functions

## Testing Strategy

### Unit Tests
- GameEvent creation and formatting
- Bot history initialization and updates
- Event index tracking
- Tool result formatting

### Integration Tests
- Full bot query flow with history
- Multi-turn conversations
- Event tracking across multiple bot queries
- Tool execution with history updates

### Manual Testing
- Play a full game with bots
- Verify bots can reference previous thoughts
- Check event log consistency
- Verify proper conversation flow

## Migration Checklist

- [ ] Phase 1: GameEvent system
  - [ ] Create GameEvent dataclass
  - [ ] Update Game model to use events
  - [ ] Update all event creation points
  - [ ] Update event consumption points
  - [ ] Update tests

- [ ] Phase 2: Bot message history
  - [ ] Create bot_message_history.py
  - [ ] Implement storage functions
  - [ ] Add history initialization

- [ ] Phase 3: LLM service updates
  - [ ] Update query_bot_with_tools signature
  - [ ] Extract tool IDs
  - [ ] Return full response content
  - [ ] Update tests

- [ ] Phase 4: Parallel bot service
  - [ ] Update BotResponse dataclass
  - [ ] Implement first query flow
  - [ ] Implement subsequent query flow
  - [ ] Update tool result handling
  - [ ] Update tests

- [ ] Phase 5: Cleanup
  - [ ] Remove deprecated LLM methods
  - [ ] Clean up tool_prompt_builder
  - [ ] Update all tests
  - [ ] Remove unused code

## Future Enhancements
- Implement prompt caching using Claude's caching feature
- Add message history persistence (database)
- Implement history trimming for very long games
- Add debug logging for message history
- Bot personality/strategy persistence across games
