"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { SearchMeta, SearchPayload } from "../lib/api";

type StoredSearch = {
  payload: SearchPayload;
  meta: SearchMeta;
  query: string;
  at: string;
};

type SearchStoreValue = {
  latest: StoredSearch | null;
  push: (value: StoredSearch) => void;
};

const KEY = "letterops.latest_search";

const SearchStoreContext = createContext<SearchStoreValue | null>(null);

export function SearchStoreProvider({ children }: { children: ReactNode }) {
  const [latest, setLatest] = useState<StoredSearch | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return;
    try {
      setLatest(JSON.parse(raw) as StoredSearch);
    } catch {
      window.localStorage.removeItem(KEY);
    }
  }, []);

  const value = useMemo<SearchStoreValue>(() => ({
    latest,
    push: (record) => {
      setLatest(record);
      window.localStorage.setItem(KEY, JSON.stringify(record));
    }
  }), [latest]);

  return <SearchStoreContext.Provider value={value}>{children}</SearchStoreContext.Provider>;
}

export function useSearchStore(): SearchStoreValue {
  const value = useContext(SearchStoreContext);
  if (!value) {
    throw new Error("useSearchStore must be used inside SearchStoreProvider");
  }
  return value;
}
