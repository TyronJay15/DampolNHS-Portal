import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useCms } from '../../hooks/useCms';
import { DEFAULT_CMS } from '../../utils/cmsDefaults';
import BrandMark from './BrandMark';
import './PostLoginLoader.css';

// The closing counterpart of PostLoginLoader, with the same layers and look. The sequence is timed in the CSS
// (overlay 0s, logo 0.2s, heading 0.5s, thanks 0.8s, status 1.1s). Sign-out itself starts at once and
// never waits for this: the overlay only stays until both the minimum below has passed and sign-out is done.
const MIN_MS = 2000;
const EXIT_MS = 500;
const REDUCED_MIN_MS = 900;
const REDUCED_EXIT_MS = 250;
const PORTAL_NAME = 'Dampol 1st NHS Grade Portal';

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

export default function SignOutLoader({ done, offline, onDone }) {
  const cms = useCms();
  const logo = cms?.footer?.logo ?? DEFAULT_CMS.footer.logo;
  const [played, setPlayed] = useState(false);
  const reduced = useRef(prefersReducedMotion());
  const finished = useRef(false);
  const overlay = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => setPlayed(true), reduced.current ? REDUCED_MIN_MS : MIN_MS);
    return () => clearTimeout(timer);
  }, []);

  // While the overlay is up, the page underneath takes no clicks (CSS) and no keyboard focus (inert).
  useEffect(() => {
    const root = document.getElementById('root');
    root?.setAttribute('inert', '');
    overlay.current?.focus();
    return () => root?.removeAttribute('inert');
  }, []);

  const leaving = played && done;

  useEffect(() => {
    if (!leaving) return undefined;
    const exit = setTimeout(() => {
      if (finished.current) return;
      finished.current = true;
      onDone?.();
    }, reduced.current ? REDUCED_EXIT_MS : EXIT_MS);
    return () => clearTimeout(exit);
  }, [leaving, onDone]);

  return createPortal(
    <div
      ref={overlay}
      tabIndex={-1}
      className={`pll is-signout${done ? ' is-done' : ''}${leaving ? ' is-leaving' : ''}`}
      role="status"
      aria-live="polite"
      aria-busy={!done}
    >
      <div className="pll-backdrop" aria-hidden="true" />
      <div className="pll-inner">
        <BrandMark logo={logo} />
        <div className="pll-text">
          <h1>Thank You!</h1>
          <i className="pll-rule" aria-hidden="true" />
          <p className="pll-thanks">Thank you for using the {PORTAL_NAME}.</p>
        </div>
        <div className="pll-status">
          <div className="pll-line" aria-hidden="true">
            <i />
          </div>
          <p>{offline ? 'Signed out on this device. The server could not be reached.' : 'Safely signing you out…'}</p>
        </div>
      </div>
    </div>,
    document.body,
  );
}
