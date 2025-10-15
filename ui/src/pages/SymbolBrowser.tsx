import { SearchMode, useSymbolSearch } from '../hooks/useSymbolSearch';
import { sampleSymbols } from '../data/sampleSymbols';
import './SymbolBrowser.css';

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

  return (
    <main className="symbol-browser">
      <section className="symbol-browser__search">
        <h1>Symbol Browser</h1>
        <p className="symbol-browser__helper">
          Filter symbols stored in Redis by ID, domain, or tag. Select a symbol to inspect all
          metadata and explore related symbols.
        </p>
        <div className="symbol-browser__search-controls">
          <label className="symbol-browser__control">
            <span>Search Mode</span>
            <select
              value={searchMode}
              onChange={(event) => setSearchMode(event.target.value as SearchMode)}
            >
              <option value="id">ID</option>
              <option value="domain">Domain</option>
              <option value="tag">Tag</option>
            </select>
          </label>
          <label className="symbol-browser__control symbol-browser__control--query">
            <span>Query</span>
            <input
              type="text"
              placeholder={`Filter by ${searchMode}`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="symbol-browser__content">
        <div className="symbol-browser__results">
          <h2>Results</h2>
          {results.length === 0 ? (
            <p className="symbol-browser__empty">No symbols matched your query.</p>
          ) : (
            <ul>
              {results.map((symbol) => (
                <li key={symbol.id}>
                  <button
                    className={selected?.id === symbol.id ? 'selected' : ''}
                    onClick={() => selectSymbol(symbol.id)}
                  >
                    <span className="symbol-id">{symbol.id}</span>
                    <span className="symbol-domain">{symbol.domain}</span>
                    <span className="symbol-tags">{symbol.tags.join(', ')}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="symbol-browser__details">
          <h2>Details</h2>
          {!selected ? (
            <p className="symbol-browser__placeholder">
              Select a symbol to see its metadata and linked symbols.
            </p>
          ) : (
            <article>
              <header>
                <h3>{selected.name}</h3>
                <p className="symbol-browser__details-subtitle">{selected.id}</p>
              </header>
              <p className="symbol-browser__summary">{selected.summary}</p>
              <dl className="symbol-browser__metadata">
                <div>
                  <dt>Domain</dt>
                  <dd>{selected.domain}</dd>
                </div>
                <div>
                  <dt>Tags</dt>
                  <dd>{selected.tags.join(', ')}</dd>
                </div>
                {Object.entries(selected.metadata).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
              <section className="symbol-browser__links">
                <h4>Linked Symbols</h4>
                {selected.linkedSymbolIds.length === 0 ? (
                  <p className="symbol-browser__empty">No linked symbols</p>
                ) : (
                  <ul>
                    {selected.linkedSymbolIds.map((id) => {
                      const symbol = sampleSymbols.find((item) => item.id === id);
                      return (
                        <li key={id}>
                          <button onClick={() => selectSymbol(id)}>
                            <span className="symbol-id">{id}</span>
                            {symbol ? <span className="symbol-name">{symbol.name}</span> : null}
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
      </section>
    </main>
  );
};

export default SymbolBrowser;
