tools = [
    {
        "name": "ask",
        "description": "Ask another player a question",
        "input_schema": {
            "thought": {"type": "string", "description": "Your thoughts, reasoning, and strategy"},
            "question": {"type": "string"},
            "target": {"type": "string", "description": "ID of the player to ask (CAN'T be the player that just asked you)"}
        },
        "required": ["thought", "question", "target"]
    },
    {
        "name": "answer",
        "description": "Answer the question just asked to you",
        "input_schema": {
            "thought": {"type": "string", "description": "Your thoughts, reasoning, and strategy"},
            "answer": {"type": "string"},
        },
        "required": ["thought", "answer"]
    },
    {
        "name": "accuse",
        "description": "Accuse another player of being a spy. Stops the game timer and forces a vote.",
        "input_schema": {
            "thought": {"type": "string", "description": "Your thoughts, reasoning, and strategy"},
            "target": {"type": "string", "description": "ID of the player to accuse"},
            "guilty": {"type": "boolean", "description": "True for guilty, false for innocent"}
        },
        "required": ["thought", "target", "guilty"]
    },
    {
        "name": "guess_location",
        "description": "Guess the location. Reveals yourself as the spy and ends the game. You win if correct and lose if not",
        "input_schema": {
            "thought": {"type": "string", "description": "Your thoughts, reasoning, and strategy"},
            "location": {"type": "string", "enum": [""]},
        },
        "required": ["thought", "location"]
    }
]