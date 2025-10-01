import React from 'react';
import { Player } from '../../../types';
import { PlayerCard } from '../../ui/PlayerCard';

interface PlayersListProps {
  players: Player[];
  currentPlayerId: string;
  title?: string;
  className?: string;
}

export function PlayersList({
  players,
  currentPlayerId,
  title = "Players",
  className = ""
}: PlayersListProps) {
  return (
    <div className={className}>
      <h3 className="text-lg font-semibold mb-2">
        {title} ({players.length})
      </h3>
      <div className="space-y-2">
        {players.map((player) => (
          <PlayerCard
            key={player.id}
            player={player}
            isCurrentPlayer={player.id === currentPlayerId}
          />
        ))}
      </div>
    </div>
  );
}