import { useEffect, useState } from "react";

// Returns value after it has stopped changing for `delay` ms.
export function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);

  return debounced;
}

// Pagination state that resets to page 1 whenever `deps` change.
// Uses a keyed reset during render instead of an effect, per
// react.dev/learn/you-might-not-need-an-effect (avoids a wasted render pass).
export function usePagination(deps) {
  const key = JSON.stringify(deps);
  const [page, setPage] = useState(1);
  const [prevKey, setPrevKey] = useState(key);

  if (prevKey !== key) {
    setPrevKey(key);
    setPage(1);
  }

  return [page, setPage];
}
