import { useCallback, useEffect, useMemo, useState } from 'react';
import { buildUrl } from '../utils/api';

const DEFAULT_LIMIT = 20;
const MIN_LIMIT = 1;
const MAX_LIMIT = 20;

const fieldStyles =
  'mt-2 w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-slate-950/40 transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-500/40';
const cardStyles =
  'rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/30 backdrop-blur';

const createRunRecord = ({ symbolDomain, symbolTag, limit }) => ({
  id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
  startedAt: new Date().toISOString(),
  status: 'running',
  params: {
    symbol_domain: symbolDomain || undefined,
    symbol_tag: symbolTag || undefined,
    limit
  },
  metrics: null,
  error: null,
  completedAt: null
});

const statusConfig = {
  running: {
    label: 'Running',
    badge: 'bg-sky-500/20 text-sky-300 border-sky-500/40'
  },
  success: {
    label: 'Completed',
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  },
  failed: {
    label: 'Failed',
    badge: 'bg-rose-500/20 text-rose-200 border-rose-500/40'
  }
};

const SymbolSync = () => {
  const [symbolDomain, setSymbolDomain] = useState('');
  const [symbolTag, setSymbolTag] = useState('');
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [history, setHistory] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastError, setLastError] = useState(null);
  const [domains, setDomains] = useState([]);
  const [domainsLoading, setDomainsLoading] = useState(false);
  const [domainsError, setDomainsError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const loadDomains = async () => {
      setDomainsLoading(true);
      setDomainsError(null);

      try {
        const endpoint = buildUrl('/domains/external');
        const response = await fetch(endpoint, {
          headers: { Accept: 'application/json' }
        });

        if (response.status === 404) {
          throw new Error(
            'Failed to load domains: external domain endpoint not found (received 404). Ensure the API exposes /domains/external.'
          );
        }

        if (!response.ok) {
          const errorText = await response.text();
          const message =
            errorText ||
            `Failed to load domains (status ${response.status}) from ${endpoint}. Ensure the local API exposes /domains/external.`;
          throw new Error(message);
        }

        const payload = await response.json();

        if (!cancelled) {
          setDomains(Array.isArray(payload) ? payload : []);
        }
      } catch (err) {
        if (!cancelled) {
          setDomainsError(err instanceof Error ? err.message : String(err));
          setDomains([]);
        }
      } finally {
        if (!cancelled) {
          setDomainsLoading(false);
        }
      }
    };

    loadDomains();

    return () => {
      cancelled = true;
    };
  }, []);

  const updateRun = useCallback((runId, updater) => {
    setHistory((previous) =>
      previous.map((run) => (run.id === runId ? { ...run, ...updater(run) } : run))
    );
  }, []);

  const startSync = useCallback(
    async (event) => {
      event.preventDefault();
      if (isSyncing) {
        return;
      }

      const numericLimit = Math.max(MIN_LIMIT, Math.min(MAX_LIMIT, Number(limit) || DEFAULT_LIMIT));
      const runRecord = createRunRecord({ symbolDomain, symbolTag, limit: numericLimit });

      setHistory((previous) => [runRecord, ...previous]);
      setIsSyncing(true);
      setLastError(null);

      const payload = {
        limit: numericLimit
      };

      if (runRecord.params.symbol_domain) {
        payload.symbol_domain = runRecord.params.symbol_domain;
      }
      if (runRecord.params.symbol_tag) {
        payload.symbol_tag = runRecord.params.symbol_tag;
      }

      try {
        const response = await fetch(buildUrl('/sync/symbols'), {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `Sync failed (${response.status})`);
        }

        const result = await response.json();
        updateRun(runRecord.id, () => ({
          status: 'success',
          completedAt: new Date().toISOString(),
          metrics: result,
          error: null
        }));
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setLastError(message);
        updateRun(runRecord.id, (run) => ({
          status: 'failed',
          completedAt: new Date().toISOString(),
          metrics: run.metrics,
          error: message
        }));
      } finally {
        setIsSyncing(false);
      }
    },
    [isSyncing, limit, symbolDomain, symbolTag, updateRun]
  );

  const currentRun = history.find((run) => run.status === 'running') ?? null;
  const lastSuccessfulRun = useMemo(
    () => history.find((run) => run.status === 'success') ?? null,
    [history]
  );

  const hasHistory = history.length > 0;

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-10">
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-white">Symbol Sync</h1>
          <p className="max-w-3xl text-sm leading-relaxed text-slate-300">
            Pull managed symbols from the external store into the local Redis cache. Configure optional
            filters, trigger a synchronisation run, and review metrics for recent executions.
          </p>
        </div>
        <form className={`${cardStyles} space-y-6`} onSubmit={startSync}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col text-sm font-medium text-slate-200">
              <span>Domain (optional)</span>
              <select
                className={fieldStyles}
                value={symbolDomain}
                disabled={domainsLoading || domains.length === 0}
                onChange={(event) => setSymbolDomain(event.target.value)}
              >
                <option value="">All domains</option>
                {domains.map((domain) => (
                  <option key={domain} value={domain}>
                    {domain}
                  </option>
                ))}
              </select>
              {domainsLoading ? (
                <span className="mt-2 text-xs text-slate-400">Loading domains…</span>
              ) : null}
              {domainsError ? (
                <span className="mt-2 text-xs text-rose-300">{domainsError}</span>
              ) : null}
            </label>
            <label className="flex flex-col text-sm font-medium text-slate-200">
              <span>Tag (optional)</span>
              <input
                className={fieldStyles}
                type="text"
                value={symbolTag}
                placeholder="Filter by tag"
                onChange={(event) => setSymbolTag(event.target.value)}
              />
            </label>
            <label className="flex flex-col text-sm font-medium text-slate-200">
              <span>Page size</span>
              <input
                className={fieldStyles}
                type="number"
                min={MIN_LIMIT}
                max={MAX_LIMIT}
                value={limit}
                onChange={(event) => setLimit(event.target.value)}
              />
              <span className="mt-2 text-xs text-slate-400">
                The external API caps each page at {MAX_LIMIT} symbols.
              </span>
            </label>
          </div>
          {lastError ? (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 px-4 py-3 text-sm text-rose-200">
              {lastError}
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <button
              className="rounded-xl bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 shadow transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
              type="submit"
              disabled={isSyncing}
            >
              {isSyncing ? 'Synchronising…' : 'Start Synchronisation'}
            </button>
            {currentRun ? (
              <span className="text-xs uppercase tracking-wider text-slate-400">
                In progress — waiting for response…
              </span>
            ) : null}
          </div>
        </form>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(260px,320px),1fr]">
        <section className={`${cardStyles} space-y-6`}>
          <header className="space-y-1">
            <h2 className="text-lg font-semibold text-white">Current Status</h2>
            <p className="text-xs uppercase tracking-wider text-slate-400">
              {currentRun ? 'Active synchronisation' : lastSuccessfulRun ? 'Last synchronisation' : 'No runs yet'}
            </p>
          </header>
          {currentRun || lastSuccessfulRun ? (
            <StatusSummary run={currentRun ?? lastSuccessfulRun} />
          ) : (
            <p className="rounded-xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-6 text-sm text-slate-400">
              Trigger a run to see synchronisation metrics.
            </p>
          )}
        </section>

        <section className={`${cardStyles} space-y-4`}>
          <header className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Run History</h2>
              <p className="text-xs uppercase tracking-wider text-slate-400">
                Most recent first
              </p>
            </div>
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{history.length}</span>
          </header>
          {hasHistory ? (
            <ul className="space-y-3">
              {history.map((run) => (
                <li key={run.id} className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                  <RunEntry run={run} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-6 text-sm text-slate-400">
              No synchronisation attempts recorded in this session.
            </p>
          )}
        </section>
      </div>
    </section>
  );
};

const StatusSummary = ({ run }) => {
  const duration = useMemo(() => {
    if (!run.completedAt) {
      return null;
    }
    const started = new Date(run.startedAt).getTime();
    const completed = new Date(run.completedAt).getTime();
    if (Number.isNaN(started) || Number.isNaN(completed)) {
      return null;
    }
    const ms = Math.max(0, completed - started);
    if (ms < 1000) {
      return `${ms} ms`;
    }
    return `${(ms / 1000).toFixed(2)} s`;
  }, [run.completedAt, run.startedAt]);

  const status = statusConfig[run.status] ?? statusConfig.running;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">Status</p>
          <p className="text-lg font-semibold text-white">{status.label}</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${status.badge}`}>
          {status.label}
        </span>
      </div>
      <dl className="grid gap-3 sm:grid-cols-2">
        <SummaryItem label="Fetched" value={run.metrics?.fetched ?? 0} />
        <SummaryItem label="Stored" value={run.metrics?.stored ?? 0} />
        <SummaryItem label="New" value={run.metrics?.new ?? 0} />
        <SummaryItem label="Updated" value={run.metrics?.updated ?? 0} />
        <SummaryItem label="Pages" value={run.metrics?.pages ?? 0} />
        <SummaryItem label="Duration" value={duration ?? '—'} />
      </dl>
      <div className="space-y-2 text-xs text-slate-400">
        <p>Started: {formatTimestamp(run.startedAt)}</p>
        {run.completedAt ? <p>Completed: {formatTimestamp(run.completedAt)}</p> : null}
        {run.params.symbol_domain ? <p>Domain filter: {run.params.symbol_domain}</p> : <p>Domain filter: All domains</p>}
        {run.params.symbol_tag ? <p>Tag filter: {run.params.symbol_tag}</p> : <p>Tag filter: All tags</p>}
        <p>Limit per page: {run.params.limit}</p>
      </div>
      {run.error ? (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 px-4 py-3 text-xs text-rose-200">
          {run.error}
        </div>
      ) : null}
    </div>
  );
};

const SummaryItem = ({ label, value }) => (
  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
    <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</dt>
    <dd className="mt-1 text-lg font-semibold text-white">{value}</dd>
  </div>
);

const RunEntry = ({ run }) => {
  const status = statusConfig[run.status] ?? statusConfig.running;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">
            {formatTimestamp(run.startedAt)}
          </p>
          <p className="text-sm font-semibold text-white">{status.label}</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wider ${status.badge}`}>
          {status.label}
        </span>
      </div>
      <dl className="grid gap-2 sm:grid-cols-2">
        <SummaryItem label="Fetched" value={run.metrics?.fetched ?? '—'} />
        <SummaryItem label="Stored" value={run.metrics?.stored ?? '—'} />
        <SummaryItem label="New" value={run.metrics?.new ?? '—'} />
        <SummaryItem label="Updated" value={run.metrics?.updated ?? '—'} />
        <SummaryItem label="Pages" value={run.metrics?.pages ?? '—'} />
      </dl>
      <div className="rounded-xl border border-slate-800 bg-slate-950/30 px-4 py-3 text-xs text-slate-300">
        <p className="font-semibold uppercase tracking-wider text-slate-400">Parameters</p>
        <ul className="mt-1 space-y-1">
          <li>Domain: {run.params.symbol_domain ?? 'All domains'}</li>
          <li>Tag: {run.params.symbol_tag ?? 'All tags'}</li>
          <li>Limit: {run.params.limit}</li>
        </ul>
      </div>
      {run.error ? (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 px-4 py-3 text-xs text-rose-200">
          {run.error}
        </div>
      ) : null}
    </div>
  );
};

const formatTimestamp = (value) => {
  if (!value) {
    return '—';
  }
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat('default', {
      dateStyle: 'medium',
      timeStyle: 'medium'
    }).format(date);
  } catch (err) {
    return value;
  }
};

export default SymbolSync;
