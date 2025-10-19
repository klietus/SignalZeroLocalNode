import { useCallback, useEffect, useRef, useState } from 'react';

import { buildApiUrl } from '../utils/api';

export const SEARCH_MODES = ['id', 'domain', 'tag'];

const DEFAULT_RESULT_LIMIT = 20;

export const useSymbolSearch = () => {
  const [searchMode, rawSetSearchMode] = useState('id');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [selectedSymbolId, setSelectedSymbolId] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [domains, setDomains] = useState([]);
  const [domainsLoading, setDomainsLoading] = useState(false);
  const [domainError, setDomainError] = useState(null);

  const selectedSymbolIdRef = useRef(selectedSymbolId);
  useEffect(() => {
    selectedSymbolIdRef.current = selectedSymbolId;
  }, [selectedSymbolId]);

  const fetchSymbolById = useCallback(async (symbolId) => {
    const trimmed = symbolId?.trim();
    if (!trimmed) {
      return null;
    }

    const response = await fetch(buildApiUrl(`/symbol/${encodeURIComponent(trimmed)}`), {
      headers: {
        Accept: 'application/json'
      }
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        errorText || `Failed to fetch symbol ${trimmed}: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }, []);

  const fetchSymbolList = useCallback(async (params) => {
    const response = await fetch(buildApiUrl('/symbols', params), {
      headers: {
        Accept: 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to fetch symbols: ${response.statusText}`);
    }

    return response.json();
  }, []);

  const fetchDomains = useCallback(async () => {
    const response = await fetch(buildApiUrl('/domains'), {
      headers: {
        Accept: 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to fetch domains: ${response.statusText}`);
    }

    return response.json();
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadDomains = async () => {
      setDomainsLoading(true);
      setDomainError(null);

      try {
        const loadedDomains = await fetchDomains();
        if (!cancelled) {
          setDomains(Array.isArray(loadedDomains) ? loadedDomains : []);
        }
      } catch (err) {
        if (!cancelled) {
          setDomainError(err instanceof Error ? err.message : String(err));
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
  }, [fetchDomains]);

  useEffect(() => {
    if (searchMode !== 'domain') {
      return;
    }

    if (domainsLoading) {
      return;
    }

    if (!domains || domains.length === 0) {
      if (query !== '') {
        setQuery('');
      }
      return;
    }

    if (query === '') {
      return;
    }

    if (!domains.includes(query)) {
      setQuery(domains[0] ?? '');
    }
  }, [domains, domainsLoading, query, searchMode]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const trimmedQuery = query.trim();

        if (searchMode === 'id' && !trimmedQuery) {
          setResults([]);
          setSelectedSymbolId(null);
          setSelectedSymbol(null);
          return;
        }

        if ((searchMode === 'domain' || searchMode === 'tag') && !trimmedQuery) {
          setResults([]);
          setSelectedSymbolId(null);
          setSelectedSymbol(null);
          return;
        }

        if (searchMode === 'id' && trimmedQuery) {
          const symbol = await fetchSymbolById(trimmedQuery);
          if (cancelled) {
            return;
          }

          if (symbol) {
            setResults([symbol]);
            setSelectedSymbolId(symbol.id);
            setSelectedSymbol(symbol);
          } else {
            setResults([]);
            setSelectedSymbolId(null);
            setSelectedSymbol(null);
          }
          return;
        }

        const params = new URLSearchParams();

        if (searchMode === 'domain' && trimmedQuery) {
          params.set('symbol_domain', trimmedQuery);
        } else if (searchMode === 'tag' && trimmedQuery) {
          params.set('symbol_tag', trimmedQuery);
        }

        params.set('limit', String(DEFAULT_RESULT_LIMIT));

        const symbols = await fetchSymbolList(params);
        if (cancelled) {
          return;
        }

        setResults(symbols);

        if (symbols.length === 0) {
          setSelectedSymbolId(null);
          setSelectedSymbol(null);
          return;
        }

        const currentSelectedId = selectedSymbolIdRef.current;
        const nextSymbol =
          symbols.find((symbol) => symbol.id === currentSelectedId) ?? symbols[0];

        setSelectedSymbolId(nextSymbol.id);
        setSelectedSymbol(nextSymbol);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setResults([]);
          setSelectedSymbolId(null);
          setSelectedSymbol(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [fetchSymbolById, fetchSymbolList, query, searchMode]);

  const selectSymbol = useCallback(
    async (symbolId) => {
      const trimmed = symbolId?.trim();
      if (!trimmed) {
        setSelectedSymbolId(null);
        setSelectedSymbol(null);
        return;
      }

      setSelectedSymbolId(trimmed);

      const fromResults = results.find((symbol) => symbol.id === trimmed);
      if (fromResults) {
        setSelectedSymbol(fromResults);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const symbol = await fetchSymbolById(trimmed);
        setSelectedSymbol(symbol);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setSelectedSymbol(null);
      } finally {
        setLoading(false);
      }
    },
    [fetchSymbolById, results]
  );

  const setSearchMode = useCallback(
    (mode) => {
      if (mode === searchMode) {
        return;
      }

      rawSetSearchMode(mode);
      setQuery('');
      setResults([]);
      setSelectedSymbolId(null);
      setSelectedSymbol(null);
      setError(null);
      selectedSymbolIdRef.current = null;
    },
    [rawSetSearchMode, searchMode]
  );

  return {
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
  };
};
