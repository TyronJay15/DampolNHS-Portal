import { useCallback, useRef, useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import { ConfirmContext } from './confirmContext';

// Mounted once in App. Components ask with useConfirm(); only one dialog is open at a time,
// and a second request cancels the first.
export function ConfirmProvider({ children }) {
  const [options, setOptions] = useState(null);
  const pending = useRef(null);

  const settle = useCallback((value) => {
    const resolve = pending.current;
    pending.current = null;
    setOptions(null);
    resolve?.(value);
  }, []);

  const confirm = useCallback((next) => {
    pending.current?.(null);
    return new Promise((resolve) => {
      pending.current = resolve;
      setOptions(next);
    });
  }, []);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {options ? <ConfirmDialog options={options} onResolve={settle} /> : null}
    </ConfirmContext.Provider>
  );
}
