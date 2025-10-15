import { useEffect, useRef } from 'react';
import { SEARCH_MODES, useSymbolSearch } from '../hooks/useSymbolSearch';

const SymbolBrowser = () => {
  const {
    searchMode,
    setSearchMode,
    query,
    setQuery,
    results,
    selectSymbol,
    selectedSymbol,
    loading,
    error,
    domains,
    domainsLoading,
    domainError
  } = useSymbolSearch();

  const queryInputRef = useRef(null);
  const domainSelectRef = useRef(null);

  useEffect(() => {
    if (searchMode === 'domain') {
      if (domainsLoading || domains.length === 0) {
        return;
      }
      domainSelectRef.current?.focus();
    } else {
      if (!queryInputRef.current) {
        return;
      }
      queryInputRef.current.focus();
      if (typeof queryInputRef.current.select === 'function') {
        queryInputRef.current.select();
      }
    }
  }, [searchMode, domainsLoading, domains.length]);

  const selected = selectedSymbol;

  const fieldStyles =
    'mt-2 w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-slate-950/40 transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-500/40';
  const cardStyles =
    'rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/30 backdrop-blur';

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10">
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-white">Symbol Browser</h1>
          <p className="max-w-3xl text-sm leading-relaxed text-slate-300">
            Filter symbols stored in Redis by ID, domain, or tag. Select a symbol to inspect all
            metadata and explore related symbols.
          </p>
        </div>
        <div className={`${cardStyles} space-y-4`}>
          <div className="grid gap-4 lg:grid-cols-[220px,1fr] lg:items-end">
            <label className="flex flex-col text-sm font-medium text-slate-200">
              <span>Search Mode</span>
              <select
                className={fieldStyles}
                value={searchMode}
                onChange={(event) => setSearchMode(event.target.value)}
              >
                {SEARCH_MODES.map((mode) => (
                  <option key={mode} value={mode}>
                    {mode === 'id' ? 'ID' : mode.charAt(0).toUpperCase() + mode.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            {searchMode === 'domain' ? (
              <label className="flex flex-col text-sm font-medium text-slate-200">
                <span>Domain</span>
              <select
                ref={domainSelectRef}
                className={fieldStyles}
                value={query}
                disabled={domains.length === 0}
                onChange={(event) => setQuery(event.target.value)}
              >
                {domainsLoading && domains.length === 0 ? (
                  <option value="">Loading domains…</option>
                ) : domains.length === 0 ? (
                  <option value="">No domains available</option>
                ) : (
                  <>
                    <option value="">Select a domain…</option>
                    {domains.map((domain) => (
                      <option key={domain} value={domain}>
                        {domain}
                      </option>
                    ))}
                  </>
                )}
              </select>
                {domainError ? (
                  <span className="mt-2 text-xs text-red-300">{domainError}</span>
                ) : null}
              </label>
            ) : (
              <label className="flex flex-col text-sm font-medium text-slate-200">
                <span>Query</span>
                <input
                  ref={queryInputRef}
                  className={fieldStyles}
                  type="text"
                  placeholder={`Filter by ${searchMode}`}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(260px,320px),1fr]">
        <div className={`${cardStyles} flex flex-col gap-4 lg:max-h-[calc(100vh-220px)] lg:overflow-y-auto`}>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Results</h2>
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              {results.length} match{results.length === 1 ? '' : 'es'}
            </span>
          </div>
          {error ? (
            <p className="rounded-xl border border-red-500/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
              {error}
            </p>
          ) : loading && results.length === 0 ? (
            <p className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-6 text-sm text-slate-400">
              Loading symbols…
            </p>
          ) : results.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-800 bg-slate-900/80 px-4 py-6 text-sm text-slate-400">
              No symbols matched your query.
            </p>
          ) : (
            <ul className="space-y-2">
              {results.map((symbol) => {
                const isSelected = selected?.id === symbol.id;
                return (
                  <li key={symbol.id}>
                    <button
                      className={`w-full rounded-xl border px-4 py-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400 ${
                        isSelected
                          ? 'border-sky-400 bg-sky-400/20 text-white shadow'
                          : 'border-slate-800 bg-slate-950/50 text-slate-200 hover:border-slate-700 hover:bg-slate-900'
                      }`}
                      onClick={() => selectSymbol(symbol.id)}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-mono text-xs uppercase tracking-wider text-slate-300">
                          {symbol.id}
                        </span>
                        {symbol.symbol_domain ? (
                          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-300">
                            {symbol.symbol_domain}
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                        {symbol.name ? (
                          <span className="font-semibold text-slate-200">{symbol.name}</span>
                        ) : null}
                        {symbol.symbol_tag ? <span>{symbol.symbol_tag}</span> : null}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className={`${cardStyles} flex flex-col gap-4 lg:max-h-[calc(100vh-220px)] lg:overflow-y-auto`}>
          <h2 className="text-lg font-semibold text-white">Details</h2>
          {loading && !selected ? (
            <p className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-6 text-sm text-slate-400">
              Loading symbol details…
            </p>
          ) : !selected ? (
            <p className="rounded-xl border border-dashed border-slate-800 bg-slate-900/80 px-4 py-6 text-sm text-slate-400">
              Select a symbol to see its metadata and linked symbols.
            </p>
          ) : (
            <article className="space-y-6">
              <header className="space-y-1">
                <h3 className="text-2xl font-semibold text-white">{selected.name ?? selected.id}</h3>
                <p className="font-mono text-xs uppercase tracking-widest text-slate-400">{selected.id}</p>
              </header>
              {selected.description ? (
                <p className="text-sm leading-relaxed text-slate-200">{selected.description}</p>
              ) : null}
              {selected.macro ? (
                <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-200">
                  {selected.macro}
                </pre>
              ) : null}
              <dl className="grid gap-4 md:grid-cols-2">
                <DetailCard label="Domain" value={selected.symbol_domain ?? '—'} />
                <DetailCard label="Tag" value={selected.symbol_tag ?? '—'} />
                <DetailCard label="Symbolic Role" value={selected.symbolic_role ?? '—'} />
                <DetailCard label="Triad" value={selected.triad ?? '—'} />
                <DetailCard label="Origin" value={selected.origin ?? '—'} />
                <DetailCard label="Version" value={selected.version ?? '—'} />
                <DetailCard label="Failure Mode" value={selected.failure_mode ?? '—'} />
              </dl>
              {selected.facets ? (
                <section className="space-y-3">
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Facets</h4>
                  <dl className="grid gap-3 md:grid-cols-2">
                    {Object.entries(selected.facets).map(([key, value]) => (
                      <DetailCard key={key} label={key} value={value} />
                    ))}
                  </dl>
                </section>
              ) : null}
              {selected.invocations && selected.invocations.length > 0 ? (
                <section className="space-y-3">
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Invocations</h4>
                  <ul className="space-y-2">
                    {selected.invocations.map((item) => (
                      <li
                        key={item}
                        className="rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-2 text-sm text-slate-200"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
              <section className="space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Linked Symbols</h4>
                {!selected.linked_patterns || selected.linked_patterns.length === 0 ? (
                  <p className="text-sm italic text-slate-400">No linked symbols</p>
                ) : (
                  <ul className="space-y-2">
                    {selected.linked_patterns.map((id) => (
                      <li key={id}>
                        <button
                          className="flex w-full flex-col items-start gap-1 rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-slate-700 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
                          onClick={() => {
                            setSearchMode('id');
                            setQuery(id);
                          }}
                        >
                          <span className="font-mono text-xs uppercase tracking-wider text-slate-300">{id}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Raw JSON</h4>
                <pre className="max-h-80 overflow-auto rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-[11px] leading-relaxed text-slate-200">
                  {JSON.stringify(selected, null, 2)}
                </pre>
              </section>
            </article>
          )}
        </div>
      </div>
    </section>
  );
};

const DetailCard = ({ label, value }) => (
  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
    <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</dt>
    <dd className="mt-1 whitespace-pre-wrap font-mono text-sm text-slate-100">{formatValue(value)}</dd>
  </div>
);

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : '—';
  }

  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }

  return value;
};

export default SymbolBrowser;
