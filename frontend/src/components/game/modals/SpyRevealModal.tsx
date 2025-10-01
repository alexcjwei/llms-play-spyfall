import React, { useState } from 'react';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';

interface SpyRevealModalProps {
  isOpen: boolean;
  onClose: () => void;
  onReveal: (location: string) => void;
  availableLocations: string[];
}

export function SpyRevealModal({
  isOpen,
  onClose,
  onReveal,
  availableLocations
}: SpyRevealModalProps) {
  const [guessedLocation, setGuessedLocation] = useState('');

  const handleReveal = () => {
    if (guessedLocation.trim()) {
      onReveal(guessedLocation.trim());
      setGuessedLocation('');
      onClose();
    }
  };

  const handleCancel = () => {
    setGuessedLocation('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleCancel}
      title="🎭 Reveal Your Identity"
      size="md"
    >
      <div className="space-y-4">
        <p className="text-gray-600">
          As the spy, you can reveal your identity and guess the location to win the game.
          If you guess correctly, you win! If you guess incorrectly, the innocents win.
        </p>

        <select
          value={guessedLocation}
          onChange={(e) => setGuessedLocation(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Select a location...</option>
          {availableLocations.map((location) => (
            <option key={location} value={location}>
              {location}
            </option>
          ))}
        </select>

        <div className="flex space-x-3">
          <Button
            variant="warning"
            onClick={handleReveal}
            disabled={!guessedLocation}
            className="flex-1 bg-purple-600 hover:bg-purple-700 focus:ring-purple-500"
          >
            Reveal & Guess
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