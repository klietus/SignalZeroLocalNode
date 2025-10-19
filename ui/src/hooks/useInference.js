import { useCallback, useEffect, useState } from 'react';

import { buildUrl } from '../utils/api';

const generateSessionId = () =>
  `session-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const STORAGE_KEY = 'inference:last-session-state';

const readPersistedState = () => {
  if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') {
      return {
        sessionId: typeof parsed.sessionId === 'string' ? parsed.sessionId : null,
        result: parsed.result ?? null
      };
    }
  } catch (error) {
    console.warn('Failed to read persisted inference state:', error);
  }

  return null;
};

const persistState = (state) => {
  if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
    return;
  }

  try {
    if (!state?.sessionId && !state?.result) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        sessionId: state.sessionId ?? null,
        result: state.result ?? null
      })
    );
  } catch (error) {
    console.warn('Failed to persist inference state:', error);
  }
};

export const useInference = () => {
  const persistedState = readPersistedState();

  const [sessionId, setSessionId] = useState(() => persistedState?.sessionId ?? generateSessionId());
  const [result, setResult] = useState(() => persistedState?.result ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    persistState({ sessionId, result });
  }, [sessionId, result]);

  const executeQuery = useCallback(
    async ({ query, sessionId: providedSessionId }) => {
      const trimmedQuery = query?.trim();
      if (!trimmedQuery) {
        const validationError = new Error('Enter a prompt to run inference.');
        setError(validationError.message);
        throw validationError;
      }

      const activeSessionId = (providedSessionId ?? sessionId)?.trim() || generateSessionId();
      if (activeSessionId !== sessionId) {
        setSessionId(activeSessionId);
      }

      setLoading(true);
      setError(null);

      try {
        const response = await fetch(buildUrl('/query'), {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            query: trimmedQuery,
            session_id: activeSessionId
          })
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `Inference failed: ${response.status} ${response.statusText}`);
        }

        const payload = await response.json();
        setResult(payload);
        return payload;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  const resetSession = useCallback(() => {
    setSessionId(generateSessionId());
    setResult(null);
    setError(null);
  }, []);

  return {
    sessionId,
    setSessionId,
    result,
    loading,
    error,
    executeQuery,
    resetSession
  };
};

export default useInference;
