import { useEffect, useState } from 'react';

export function useNowTicker(intervalMs = 1000) {
  const [nowMs, setNowMs] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setNowMs(Date.now());
    }, intervalMs);

    return () => {
      clearInterval(interval);
    };
  }, [intervalMs]);

  return nowMs;
}
