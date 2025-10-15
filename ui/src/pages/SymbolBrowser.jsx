import { SEARCH_MODES, useSymbolSearch } from '../hooks/useSymbolSearch';
import { sampleSymbols } from '../data/sampleSymbols';

const SymbolBrowser = () => {
  const {
    searchMode,
    setSearchMode,
    query,
    setQuery,
    results,
    selectSymbol,
    selectedSymbol
  } = useSymbolSearch();

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
            <label className="flex flex-col text-sm font-medium text-slate-200">
              <span>Query</span>
              <input
                className={fieldStyles}
                type="text"
                placeholder={`Filter by ${searchMode}`}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
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
          {results.length === 0 ? (
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
                      <span className="font-mono text-xs uppercase tracking-wider text-slate-300">
                        {symbol.id}
                      </span>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                        <span className="font-semibold text-slate-200">{symbol.domain}</span>
                        <span>{symbol.tags.join(', ')}</span>
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
          {!selected ? (
            <p className="rounded-xl border border-dashed border-slate-800 bg-slate-900/80 px-4 py-6 text-sm text-slate-400">
              Select a symbol to see its metadata and linked symbols.
            </p>
          ) : (
            <article className="space-y-6">
              <header className="space-y-1">
                <h3 className="text-2xl font-semibold text-white">{selected.name}</h3>
                <p className="font-mono text-xs uppercase tracking-widest text-slate-400">
                  {selected.id}
                </p>
              </header>
              <p className="text-sm leading-relaxed text-slate-200">{selected.summary}</p>
              <dl className="grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                  <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Domain
                  </dt>
                  <dd className="mt-1 font-mono text-sm text-slate-100">{selected.domain}</dd>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                  <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tags</dt>
                  <dd className="mt-1 font-mono text-sm text-slate-100">{selected.tags.join(', ')}</dd>
                </div>
                {Object.entries(selected.metadata).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                    <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      {key}
                    </dt>
                    <dd className="mt-1 font-mono text-sm text-slate-100">{String(value)}</dd>
                  </div>
                ))}
              </dl>
              <section className="space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                  Linked Symbols
                </h4>
                {selected.linkedSymbolIds.length === 0 ? (
                  <p className="text-sm italic text-slate-400">No linked symbols</p>
                ) : (
                  <ul className="space-y-2">
                    {selected.linkedSymbolIds.map((id) => {
                      const symbol = sampleSymbols.find((item) => item.id === id);
                      return (
                        <li key={id}>
                          <button
                            className="flex w-full flex-col items-start gap-1 rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-slate-700 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
                            onClick={() => selectSymbol(id)}
                          >
                            <span className="font-mono text-xs uppercase tracking-wider text-slate-300">
                              {id}
                            </span>
                            {symbol ? (
                              <span className="text-sm font-medium text-slate-100">{symbol.name}</span>
                            ) : null}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>
            </article>
          )}
        </div>
      </div>
    </section>
  );
};

export default SymbolBrowser;
