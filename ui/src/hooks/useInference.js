import { useCallback, useState } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

const buildUrl = (path) => `${API_BASE_URL}${path}`;

const generateSessionId = () =>
  `session-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export const useInference = () => {
  const [sessionId, setSessionId] = useState(() => generateSessionId());
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
        setResult(null);
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
