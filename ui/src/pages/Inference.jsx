import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useNavigate } from 'react-router-dom';
import useInference from '../hooks/useInference';

const cardStyles =
  'rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/30 backdrop-blur';
const fieldStyles =
  'mt-2 w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-slate-950/40 transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-500/40';

const PROMPT_STORAGE_KEY = 'inference:last-prompt';

const readPersistedPrompt = () => {
  if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
    return '';
  }

  try {
    return window.localStorage.getItem(PROMPT_STORAGE_KEY) ?? '';
  } catch (error) {
    console.warn('Failed to read persisted inference prompt:', error);
    return '';
  }
};

const Inference = () => {
  const {
    sessionId,
    setSessionId,
    executeQuery,
    resetSession,
    loading,
    error,
    result
  } = useInference();

  const [prompt, setPrompt] = useState(() => readPersistedPrompt());
  const [showDetails, setShowDetails] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
      return;
    }

    try {
      if (!prompt) {
        window.localStorage.removeItem(PROMPT_STORAGE_KEY);
      } else {
        window.localStorage.setItem(PROMPT_STORAGE_KEY, prompt);
      }
    } catch (error) {
      console.warn('Failed to persist inference prompt:', error);
    }
  }, [prompt]);

  const commands = useMemo(() => (Array.isArray(result?.commands) ? result.commands : []), [result]);
  const intermediateSteps = useMemo(
    () => (Array.isArray(result?.intermediate_responses) ? result.intermediate_responses : []),
    [result]
  );
  const symbolsUsed = useMemo(() => (Array.isArray(result?.symbols_used) ? result.symbols_used : []), [result]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setShowDetails(false);

    try {
      await executeQuery({ query: prompt, sessionId });
    } catch (err) {
      // Error state is handled by the hook; no-op here to avoid console noise.
    }
  };

  const handleToggleDetails = () => {
    if (!result) {
      return;
    }
    setShowDetails((previous) => !previous);
  };

  const handleSessionChange = (event) => {
    setSessionId(event.target.value);
  };

  const handleNewSession = () => {
    setPrompt('');
    setShowDetails(false);
    resetSession();
  };

  const finalReply =
    typeof result?.reply === 'string'
      ? result.reply
      : result?.reply !== undefined
        ? JSON.stringify(result.reply, null, 2)
        : '';

  const renderMarkdown = (content) => {
    const text = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
    return <ReactMarkdown className="markdown-body">{text}</ReactMarkdown>;
  };

  const handleSymbolClick = (symbol) => {
    if (!symbol) {
      return;
    }
    navigate({ pathname: '/', search: `?symbolId=${encodeURIComponent(symbol)}` });
  };

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-white">Inference Console</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-300">
          Run questions against the Signal Zero reasoning stack. Each response can be expanded to review
          intermediate reasoning phases, executed commands, and symbols that were used.
        </p>
      </header>

      <form className={`${cardStyles} space-y-6`} onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-200" htmlFor="inference-prompt">
            Prompt
          </label>
          <textarea
            id="inference-prompt"
            className={`${fieldStyles} min-h-[140px] resize-y`}
            placeholder="Ask a question or describe the task you want the agents to complete..."
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={loading}
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr),auto] lg:items-end">
          <label className="flex flex-col text-sm font-medium text-slate-200">
            <span>Session ID</span>
            <input
              className={fieldStyles}
              type="text"
              value={sessionId}
              onChange={handleSessionChange}
              placeholder="Generated automatically"
              disabled={loading}
            />
            <span className="mt-1 text-xs text-slate-400">
              Sessions keep context between queries. Start a new session to clear conversation memory.
            </span>
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
              onClick={handleNewSession}
              disabled={loading}
            >
              New Session
            </button>
            <button
              type="submit"
              className="rounded-xl border border-sky-500 bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 shadow transition hover:border-sky-400 hover:bg-sky-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400 disabled:cursor-not-allowed disabled:border-slate-700 disabled:bg-slate-800 disabled:text-slate-400"
              disabled={loading}
            >
              {loading ? 'Running…' : 'Run Inference'}
            </button>
          </div>
        </div>

        {error ? (
          <p className="rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        ) : null}
      </form>

      <section className={`${cardStyles} space-y-5`}>
        <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Latest Response</h2>
            <p className="text-xs uppercase tracking-wider text-slate-400">Session {sessionId || '—'}</p>
          </div>
          {result ? (
            <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-mono text-slate-300">
              History length: {result?.history_length ?? 0}
            </div>
          ) : null}
        </header>

        {!result ? (
          <p className="rounded-xl border border-dashed border-slate-800 bg-slate-950/50 px-4 py-6 text-sm text-slate-400">
            Run an inference to see responses here.
          </p>
        ) : (
          <div className="space-y-4">
            <button
              type="button"
              onClick={handleToggleDetails}
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-5 py-4 text-left transition hover:border-slate-700 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-base font-semibold text-white">Assistant Reply</h3>
                <span className="text-xs font-medium uppercase tracking-widest text-slate-400">
                  {showDetails ? 'Hide details' : 'Show details'}
                </span>
              </div>
              <div className="mt-3 rounded-xl border border-slate-800/60 bg-slate-950/40 px-4 py-3">
                {renderMarkdown(finalReply)}
              </div>
              <p className="mt-3 text-xs text-slate-400">
                Click to {showDetails ? 'collapse' : 'reveal'} intermediate steps and artifacts.
              </p>
            </button>

            {showDetails ? (
              <div className="space-y-6">
                <DetailSection title="Intermediate Phases">
                  {intermediateSteps.length === 0 ? (
                    <p className="text-sm text-slate-400">No intermediate responses were returned.</p>
                  ) : (
                    <ul className="space-y-3">
                      {intermediateSteps.map((phase, index) => {
                        const phaseId = phase?.phase_id ?? `phase-${index + 1}`;
                        const workflow = phase?.workflow ?? 'workflow';
                        const response = phase?.response ?? '—';
                        return (
                          <li
                            key={`${phaseId}-${workflow}-${index}`}
                            className="rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                                {phaseId}
                              </span>
                              <span className="text-[10px] uppercase tracking-widest text-slate-500">
                                {workflow}
                              </span>
                            </div>
                            <div className="mt-2 rounded-lg border border-slate-800/60 bg-slate-950/40 px-3 py-2">
                              {renderMarkdown(response)}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </DetailSection>

                <DetailSection title="Commands">
                  {commands.length === 0 ? (
                    <p className="text-sm text-slate-400">No commands executed.</p>
                  ) : (
                    <ul className="space-y-2 text-sm text-slate-200">
                      {commands.map((command, index) => (
                        <li
                          key={index}
                          className="rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3 text-xs text-slate-100"
                        >
                          <pre className="whitespace-pre-wrap leading-relaxed">{JSON.stringify(command, null, 2)}</pre>
                        </li>
                      ))}
                    </ul>
                  )}
                </DetailSection>

                <DetailSection title="Symbols Used">
                  {symbolsUsed.length === 0 ? (
                    <p className="text-sm text-slate-400">No symbols were attached to this response.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {symbolsUsed.map((symbol) => (
                        <button
                          type="button"
                          key={symbol}
                          className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-mono text-slate-200 transition hover:border-sky-500 hover:text-sky-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
                          onClick={() => handleSymbolClick(symbol)}
                          title="View symbol details"
                        >
                          {symbol}
                        </button>
                      ))}
                    </div>
                  )}
                </DetailSection>

                <DetailSection title="Raw Payload">
                  <pre className="max-h-80 overflow-auto rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-[11px] leading-relaxed text-slate-200">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </DetailSection>
              </div>
            ) : null}
          </div>
        )}
      </section>
    </section>
  );
};

const DetailSection = ({ title, children }) => {
  return (
    <section className="space-y-2">
      <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">{title}</h4>
      {children}
    </section>
  );
};

export default Inference;
