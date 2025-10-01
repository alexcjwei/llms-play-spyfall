import React, { useState } from 'react';
import { useGameContext } from '../../../context/GameContext';
import { GameHeader } from './GameHeader';
import { MessageHistory } from './MessageHistory';
import { InputSection } from './InputSection';
import { VotingSection } from './VotingSection';
import { GameResults } from './GameResults';
import { ActionButtons } from './ActionButtons';
import { PlayersList } from '../lobby/PlayersList';
import { AccusationModal } from '../modals/AccusationModal';
import { SpyRevealModal } from '../modals/SpyRevealModal';

export default function GameBoard() {
  const {
    gameState,
    playerId,
    askQuestion,
    giveAnswer,
    accusePlayer,
    vote,
    spyGuessLocation
  } = useGameContext();

  const [showAccuseModal, setShowAccuseModal] = useState(false);
  const [showSpyRevealModal, setShowSpyRevealModal] = useState(false);

  if (!gameState) {
    return <div>Loading...</div>;
  }

  const currentPlayer = gameState.players.find(p => p.id === playerId);
  const hasAlreadyAccused = currentPlayer?.hasAccusedThisRound || false;

  const handleAccuse = (target: string) => {
    accusePlayer(target);
  };

  const handleSpyReveal = (location: string) => {
    spyGuessLocation(location);
  };

  return (
    <div className="max-w-6xl mx-auto bg-white rounded-lg shadow p-6">
      <GameResults gameState={gameState} />

      <GameHeader gameState={gameState} />

      {/* Players list */}
      <PlayersList
        players={gameState.players}
        currentPlayerId={playerId}
        title="Players"
        className="mb-6"
      />

      <MessageHistory gameState={gameState} />

      <InputSection
        gameState={gameState}
        playerId={playerId}
        onAskQuestion={askQuestion}
        onGiveAnswer={giveAnswer}
      />

      <VotingSection
        gameState={gameState}
        playerId={playerId}
        onVote={vote}
        onAccuse={() => setShowAccuseModal(true)}
      />

      <ActionButtons
        gameState={gameState}
        onAccuse={() => setShowAccuseModal(true)}
        onSpyReveal={() => setShowSpyRevealModal(true)}
        hasAlreadyAccused={hasAlreadyAccused}
      />

      {/* Modals */}
      <AccusationModal
        isOpen={showAccuseModal}
        onClose={() => setShowAccuseModal(false)}
        onAccuse={handleAccuse}
        players={gameState.players}
        currentPlayerId={playerId}
      />

      <SpyRevealModal
        isOpen={showSpyRevealModal}
        onClose={() => setShowSpyRevealModal(false)}
        onReveal={handleSpyReveal}
        availableLocations={gameState.availableLocations || []}
      />
    </div>
  );
}