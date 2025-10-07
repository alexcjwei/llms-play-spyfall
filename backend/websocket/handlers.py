"""WebSocket message handlers"""
import logging
import json
from typing import Optional

from models import Player
from websocket.connection_manager import connection_manager
from services import game_service

logger = logging.getLogger(__name__)

# Will be injected by main.py
bot_orchestrator = None


def set_bot_orchestrator(orchestrator):
    """Set the bot orchestrator (called from main.py after initialization)"""
    global bot_orchestrator
    bot_orchestrator = orchestrator


async def handle_join_game(client_id: str, message: dict):
    """Handle player joining a game"""
    game_id = message.get("game_id", "default")
    player_name = message.get("player_name", f"Player_{client_id[:8]}")
    is_bot = message.get("is_bot", False)

    # Create game if it doesn't exist
    if not game_service.get_game(game_id):
        game_service.create_game(game_id)

    game = game_service.get_game(game_id)

    # Check if player is reconnecting (already exists in game)
    success, error = game_service.reconnect_player(game_id, client_id)
    if success:
        # Player is reconnecting
        await connection_manager.send_game_state(game_id)
        response = {
            "type": "rejoin_success",
            "game_id": game_id,
            "player_id": client_id,
        }
        await connection_manager.send_personal_message(json.dumps(response), client_id)
        return

    # Create new player
    player = Player(id=client_id, name=player_name, is_bot=is_bot, is_connected=True)

    success, error = game_service.add_player_to_game(game_id, player)
    if success:
        # Send game state to all players
        await connection_manager.send_game_state(game_id)

        # Send join confirmation to the joining player
        response = {"type": "join_success", "game_id": game_id, "player_id": client_id}
        await connection_manager.send_personal_message(json.dumps(response), client_id)
    else:
        # Failed to join
        error_response = {
            "type": "join_error",
            "message": error or "Cannot join game",
        }
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)


async def handle_start_game(client_id: str, message: dict):
    """Handle game start request"""
    game_id = message.get("game_id")
    player_count = message.get("player_count", 3)

    if not game_id:
        error_response = {"type": "start_error", "message": "Game ID required"}
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)
        return

    game = game_service.get_game(game_id)
    if not game:
        error_response = {"type": "start_error", "message": "Game not found"}
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)
        return

    success, error = game_service.start_game(game_id, client_id, player_count)
    if success:
        # Send updated game state to all players
        await connection_manager.send_game_state(game_id)

        # Check if it's now a bot's turn - use new parallel bot system
        if bot_orchestrator:
            bot_orchestrator.schedule_parallel_bot_action(game_id, delay=1)

        # Send start confirmation
        game = game_service.get_game(game_id)
        response = {"type": "game_started", "game_id": game_id}
        await connection_manager.broadcast_to_game(json.dumps(response), game)
    else:
        error_response = {
            "type": "start_error",
            "message": error or "Cannot start game",
        }
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)


async def handle_ask_question(client_id: str, message: dict):
    """Handle player asking a question"""
    game_id = message.get("game_id")
    content = message.get("content")
    target_id = message.get("target")

    if not game_id:
        return

    game = game_service.get_game(game_id)
    if not game:
        return

    if game.ask_question(client_id, target_id, content):
        logger.info(f"Question asked: {client_id} -> {target_id}: {content}")
        # Send updated game state to all players
        await connection_manager.send_game_state(game_id)

        # Use new parallel bot system to query all bots after turn
        if bot_orchestrator:
            bot_orchestrator.schedule_parallel_bot_action(game_id, delay=1)
    else:
        # Send error to the requesting player
        error_response = {
            "type": "question_error",
            "message": "Cannot ask question (not your turn or invalid target)",
        }
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)


async def handle_give_answer(client_id: str, message: dict):
    """Handle player giving an answer"""
    game_id = message.get("game_id")
    content = message.get("content")

    if not game_id:
        return

    game = game_service.get_game(game_id)
    if not game:
        return

    if game.give_answer(client_id, content):
        logger.info(f"Answer given: {client_id}: {content}")
        # Send updated game state to all players
        await connection_manager.send_game_state(game_id)

        # Use new parallel bot system to query all bots after turn
        if bot_orchestrator:
            bot_orchestrator.schedule_parallel_bot_action(game_id, delay=1)
    else:
        # Send error to the requesting player
        error_response = {
            "type": "answer_error",
            "message": "Cannot give answer (not your turn)",
        }
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)


async def handle_accuse_player(client_id: str, message: dict):
    """Handle player making an accusation"""
    game_id = message.get("game_id")
    accused_id = message.get("target")

    if not game_id:
        error_response = {"type": "accusation_error", "message": "Game ID required"}
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)
        return

    game = game_service.get_game(game_id)
    if not game:
        error_response = {"type": "accusation_error", "message": "Game not found"}
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)
        return

    # Use appropriate accusation method based on game status
    from models import GameStatus
    if game.status == GameStatus.END_OF_ROUND_VOTING:
        success = game.make_end_of_round_accusation(client_id, accused_id)
        accusation_type = "end-of-round"
        response_type = "end_of_round_accusation_made"
    else:
        success = game.stop_clock_for_accusation(client_id, accused_id)
        accusation_type = "mid-game"
        response_type = "accusation_made"

    if success:
        logger.info(f"Player {client_id} made {accusation_type} accusation against {accused_id} in game {game_id}")

        # Cancel any pending bot actions - accusation interrupts everything
        if bot_orchestrator:
            bot_orchestrator.cancel_pending_task(game_id)

        # Send updated game state to all players
        await connection_manager.send_game_state(game_id)

        # Notify all players about the accusation
        accuser_name = next((p.name for p in game.players if p.id == client_id), "Unknown")
        accused_name = next((p.name for p in game.players if p.id == accused_id), "Unknown")

        response = {
            "type": response_type,
            "accuser": accuser_name,
            "accused": accused_name,
            "game_id": game_id,
        }
        await connection_manager.broadcast_to_game(json.dumps(response), game)

        # Use new parallel bot system for voting/accusations
        # Add small delay to ensure human player receives WebSocket messages first
        if bot_orchestrator:
            bot_orchestrator.schedule_parallel_bot_action(game_id, delay=1)
    else:
        error_response = {
            "type": "accusation_error",
            "message": "Cannot make accusation (game not in progress, already accused this round, or clock stopped)",
        }
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)


async def handle_vote(client_id: str, message: dict):
    """Handle voting on an accusation"""
    game_id = message.get("game_id")
    vote = message.get("vote")  # True for guilty, False for innocent

    if not game_id:
        return

    game = game_service.get_game(game_id)
    if not game:
        return

    # Use appropriate voting method based on game status
    from models import GameStatus
    if game.status == GameStatus.END_OF_ROUND_VOTING:
        success = game.vote_on_end_of_round_accusation(client_id, vote)
        vote_type = "end-of-round"
    else:
        success = game.vote_on_accusation(client_id, vote)
        vote_type = "mid-game"

    if success:
        logger.info(f"Player {client_id} voted {vote} in {vote_type} voting in game {game_id}")

        # Send updated game state to all players
        await connection_manager.send_game_state(game_id)

        # Use new parallel bot system for voting/accusations
        # Add small delay to ensure human player receives WebSocket messages first
        if bot_orchestrator:
            bot_orchestrator.schedule_parallel_bot_action(game_id, delay=1)


async def handle_spy_guess_location(client_id: str, message: dict):
    """Handle spy guessing the location"""
    game_id = message.get("game_id")
    guessed_location = message.get("location")

    if not game_id:
        error_response = {"type": "spy_guess_error", "message": "Game ID required"}
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)
        return

    game = game_service.get_game(game_id)
    if not game:
        error_response = {"type": "spy_guess_error", "message": "Game not found"}
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)
        return

    if game.spy_guess_location(client_id, guessed_location):
        logger.info(f"Spy {client_id} guessed location: {guessed_location} in game {game_id}")

        # Cancel any pending bot actions - game is ending
        if bot_orchestrator:
            bot_orchestrator.cancel_pending_task(game_id)

        # Send updated game state to all players
        await connection_manager.send_game_state(game_id)

        # Notify all players about the spy's guess
        spy_name = next((p.name for p in game.players if p.id == client_id), "Unknown")

        response = {
            "type": "spy_revealed",
            "spy": spy_name,
            "guessed_location": guessed_location,
            "actual_location": game.location.name if game.location else "Unknown",
            "correct": game.winner == "spy",
            "game_id": game_id,
        }
        await connection_manager.broadcast_to_game(json.dumps(response), game)
    else:
        error_response = {
            "type": "spy_guess_error",
            "message": "Cannot guess location (not the spy, game not in progress, or clock stopped)",
        }
        await connection_manager.send_personal_message(json.dumps(error_response), client_id)


async def handle_client_disconnect(client_id: str):
    """Handle client disconnection"""
    # Mark player as disconnected in all games they're part of
    for game_id, game in list(game_service.active_games.items()):
        success, error = game_service.disconnect_player(game_id, client_id)
        if success:
            # Send updated game state to remaining players
            await connection_manager.send_game_state(game_id)

            player = next((p for p in game.players if p.id == client_id), None)
            if player:
                response = {
                    "type": "player_disconnected",
                    "player_id": client_id,
                    "player_name": player.name,
                }
                await connection_manager.broadcast_to_game(json.dumps(response), game)
