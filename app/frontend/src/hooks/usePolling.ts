import { useEffect, useRef } from 'react';

/** callback을 즉시 한 번 실행하고, 이후 intervalMs마다 다시 실행한다. */
export function usePolling(callback: () => void, intervalMs: number) {
  const saved = useRef(callback);

  useEffect(() => {
    saved.current = callback;
  }, [callback]);

  useEffect(() => {
    saved.current();
    const id = window.setInterval(() => saved.current(), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
}
