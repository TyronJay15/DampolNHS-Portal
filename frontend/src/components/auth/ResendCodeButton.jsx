import { useEffect, useState } from 'react';

// "Resend code" that counts down until the server allows another code (availableAt is a timestamp in ms).
export default function ResendCodeButton({ availableAt, onResend, busy }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (availableAt <= Date.now()) return undefined;
    const timer = setInterval(() => {
      const tick = Date.now();
      setNow(tick);
      if (tick >= availableAt) clearInterval(timer);
    }, 1000);
    return () => clearInterval(timer);
  }, [availableAt]);

  const left = Math.max(0, Math.ceil((availableAt - now) / 1000));
  return (
    <button className="btn btn-secondary" type="button" onClick={onResend} disabled={busy || left > 0}>
      {busy ? 'Sending…' : left ? `Resend code in ${left}s` : 'Resend code'}
    </button>
  );
}
