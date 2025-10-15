import { useMemo, useState } from 'react';
import { sampleSymbols } from '../data/sampleSymbols';

export const SEARCH_MODES = ['id', 'domain', 'tag'];

export const useSymbolSearch = () => {
  const [searchMode, setSearchMode] = useState('id');
  const [query, setQuery] = useState('');
  const [selectedSymbolId, setSelectedSymbolId] = useState(null);

  const results = useMemo(() => {
    const trimmedQuery = query.trim().toLowerCase();

    const byId = (left, right) => left.id.localeCompare(right.id);

    if (!trimmedQuery) {
      return [...sampleSymbols].sort(byId);
    }

    switch (searchMode) {
      case 'id':
        return sampleSymbols
          .filter((symbol) => symbol.id.toLowerCase().includes(trimmedQuery))
          .sort(byId);
      case 'domain':
        return sampleSymbols
          .filter((symbol) => symbol.domain.toLowerCase().includes(trimmedQuery))
          .sort(byId);
      case 'tag':
        return sampleSymbols
          .filter((symbol) =>
            symbol.tags.some((tag) => tag.toLowerCase().includes(trimmedQuery))
          )
          .sort(byId);
      default:
        return [...sampleSymbols].sort(byId);
    }
  }, [query, searchMode]);

  const selectedSymbol = useMemo(() => {
    if (selectedSymbolId) {
      return sampleSymbols.find((symbol) => symbol.id === selectedSymbolId) ?? null;
    }

    if (results.length === 1) {
      return results[0];
    }

    return null;
  }, [results, selectedSymbolId]);

  const selectSymbol = (symbolId) => {
    setSelectedSymbolId(symbolId);
  };

  return {
    searchMode,
    setSearchMode,
    query,
    setQuery,
    results,
    selectSymbol,
    selectedSymbol
  };
};
