import { useState, useCallback } from 'react';

/**
 * Hook for managing modal open/close state
 */
export function useModalState(initialState = false) {
  const [isOpen, setIsOpen] = useState(initialState);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen(prev => !prev), []);

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}

/**
 * Hook for managing multiple modals
 */
export function useMultipleModals<T extends string>(modalNames: T[]) {
  const [openModals, setOpenModals] = useState<Set<T>>(new Set());

  const openModal = useCallback((name: T) => {
    setOpenModals(prev => new Set(prev).add(name));
  }, []);

  const closeModal = useCallback((name: T) => {
    setOpenModals(prev => {
      const newSet = new Set(prev);
      newSet.delete(name);
      return newSet;
    });
  }, []);

  const isModalOpen = useCallback((name: T) => {
    return openModals.has(name);
  }, [openModals]);

  const closeAllModals = useCallback(() => {
    setOpenModals(new Set());
  }, []);

  return {
    openModal,
    closeModal,
    isModalOpen,
    closeAllModals,
  };
}