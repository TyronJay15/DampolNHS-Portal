import { useCallback, useState } from 'react';
import { MAX_COMPARE, readCompare, writeCompare } from './compareStore';

export default function useCompare() {
  const [codes, setCodes] = useState(readCompare);

  const toggle = useCallback((code) => {
    setCodes((current) => {
      const next = current.includes(code)
        ? current.filter((item) => item !== code)
        : current.length >= MAX_COMPARE
          ? current
          : [...current, code];
      writeCompare(next);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    writeCompare([]);
    setCodes([]);
  }, []);

  return { codes, toggle, clear, full: codes.length >= MAX_COMPARE };
}
