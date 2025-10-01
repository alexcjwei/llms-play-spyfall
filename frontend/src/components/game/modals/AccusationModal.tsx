import React, { useState } from 'react';
import { Player } from '../../../types';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';

interface AccusationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccuse: (target: string) => void;
  players: Player[];
  currentPlayerId: string;
}

export function AccusationModal({
  isOpen,
  onClose,
  onAccuse,
  players,
  currentPlayerId
}: AccusationModalProps) {
  const [accuseTarget, setAccuseTarget] = useState('');

  const otherPlayers = players.filter(p => p.id !== currentPlayerId);

  const handleAccuse = () => {
    if (accuseTarget) {
      onAccuse(accuseTarget);
      setAccuseTarget('');
      onClose();
    }
  };

  const handleCancel = () => {
    setAccuseTarget('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleCancel}
      title="🚨 Accuse Player"
      size="md"
    >
      <div className="space-y-4">
        <p className="text-gray-600">
          Who do you think is the spy? This will immediately stop the clock and start a voting phase.
        </p>

        <select
          value={accuseTarget}
          onChange={(e) => setAccuseTarget(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="">Select player to accuse...</option>
          {otherPlayers.map((player) => (
            <option key={player.id} value={player.id}>
              {player.name} {player.isBot ? '(Bot)' : ''}
            </option>
          ))}
        </select>

        <div className="flex space-x-3">
          <Button
            variant="danger"
            onClick={handleAccuse}
            disabled={!accuseTarget}
            className="flex-1"
          >
            Accuse
          </Button>
          <Button
            variant="secondary"
            onClick={handleCancel}
            className="flex-1"
          >
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  );
}