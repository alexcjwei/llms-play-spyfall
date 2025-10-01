import { useState, useCallback } from 'react';

/**
 * Hook for managing input state with validation and submission
 */
export function useInputState<T = string>(
  initialValue: T,
  onSubmit?: (value: T) => void,
  validator?: (value: T) => boolean
) {
  const [value, setValue] = useState<T>(initialValue);
  const [error, setError] = useState<string | null>(null);

  const updateValue = useCallback((newValue: T) => {
    setValue(newValue);
    if (error) setError(null);
  }, [error]);

  const submit = useCallback(() => {
    if (validator && !validator(value)) {
      setError('Invalid input');
      return false;
    }

    if (onSubmit) {
      onSubmit(value);
    }

    setValue(initialValue);
    setError(null);
    return true;
  }, [value, validator, onSubmit, initialValue]);

  const reset = useCallback(() => {
    setValue(initialValue);
    setError(null);
  }, [initialValue]);

  const isValid = validator ? validator(value) : true;

  return {
    value,
    setValue: updateValue,
    submit,
    reset,
    error,
    setError,
    isValid,
  };
}

/**
 * Hook for managing question/answer input with target selection
 */
export function useQuestionInput(
  onSubmit: (question: string, target: string) => void
) {
  const questionInput = useInputState('');
  const [selectedTarget, setSelectedTarget] = useState('');

  const submit = useCallback(() => {
    if (questionInput.value.trim() && selectedTarget) {
      onSubmit(questionInput.value.trim(), selectedTarget);
      questionInput.reset();
      setSelectedTarget('');
      return true;
    }
    return false;
  }, [questionInput, selectedTarget, onSubmit]);

  const canSubmit = questionInput.value.trim() && selectedTarget;

  return {
    question: questionInput.value,
    setQuestion: questionInput.setValue,
    selectedTarget,
    setSelectedTarget,
    submit,
    canSubmit,
    reset: () => {
      questionInput.reset();
      setSelectedTarget('');
    },
  };
}