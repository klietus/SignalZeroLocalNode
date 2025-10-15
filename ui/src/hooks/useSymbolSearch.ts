import { Dispatch, SetStateAction, useMemo, useState } from 'react';
import { sampleSymbols, SymbolRecord } from '../data/sampleSymbols';

export type SearchMode = 'id' | 'domain' | 'tag';

interface UseSymbolSearchResult {
  searchMode: SearchMode;
  setSearchMode: Dispatch<SetStateAction<SearchMode>>;
  query: string;
  setQuery: Dispatch<SetStateAction<string>>;
  results: SymbolRecord[];
  selectSymbol: (symbolId: string) => void;
  selectedSymbol: SymbolRecord | null;
}

export const useSymbolSearch = (): UseSymbolSearchResult => {
  const [searchMode, setSearchMode] = useState<SearchMode>('id');
  const [query, setQuery] = useState('');
  const [selectedSymbolId, setSelectedSymbolId] = useState<string | null>(null);

  const results = useMemo(() => {
    const trimmedQuery = query.trim().toLowerCase();

    const byId = (left: SymbolRecord, right: SymbolRecord) =>
      left.id.localeCompare(right.id);

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

  const selectSymbol = (symbolId: string) => {
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
