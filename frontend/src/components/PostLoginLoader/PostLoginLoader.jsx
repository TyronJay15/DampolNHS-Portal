import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useCms } from '../../hooks/useCms';
import { DEFAULT_CMS } from '../../utils/cmsDefaults';
import BrandMark from './BrandMark';
import './PostLoginLoader.css';

// The sequence is timed in the CSS (overlay 0s, logo 0.4s, accent 0.9s, name 1.2s, tagline 1.6s,
// status 2.0s, progress 2.0-3.8s). The finished composition is held until PLAY_MS, then a 500ms exit
// while the dashboard opens underneath.
const PLAY_MS = 4200;
const EXIT_MS = 500;
const REDUCED_PLAY_MS = 1800;
const REDUCED_EXIT_MS = 250;
// Safety net: never hang on a screen the dashboard side forgot to release.
const MAX_WAIT_MS = 15000;

const MESSAGE = {
  student: 'Preparing your student dashboard...',
  teacher: 'Preparing your teacher dashboard...',
  head_teacher: 'Preparing your academic dashboard...',
  admin: 'Preparing your administration dashboard...',
};

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

// Visual layer only. Two sibling layers inside a fixed overlay above the page:
//   .pll-backdrop  blurs and darkens whatever is behind it (the login page, then the dashboard)
//   .pll-inner     the logo and text, never inside the blurred element, so it stays sharp
// onLeave fires once when the exit begins (the caller navigates then); onDone when the overlay is gone.
export default function PostLoginLoader({ role, ready = true, onLeave, onDone }) {
  const cms = useCms();
  const logo = cms?.footer?.logo ?? DEFAULT_CMS.footer.logo;
  const school = cms?.footer?.brandName || DEFAULT_CMS.footer.brandName;
  const tagline = cms?.footer?.brandTagline || DEFAULT_CMS.footer.brandTagline;
  const [logoReady, setLogoReady] = useState(!logo);
  const [played, setPlayed] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const left = useRef(false);
  const finished = useRef(false);
  const reduced = useRef(prefersReducedMotion());

  useEffect(() => {
    const play = setTimeout(() => setPlayed(true), reduced.current ? REDUCED_PLAY_MS : PLAY_MS);
    const cap = setTimeout(() => setTimedOut(true), MAX_WAIT_MS);
    return () => {
      clearTimeout(play);
      clearTimeout(cap);
    };
  }, []);

  // Leave once the whole sequence has played AND the dashboard side is ready (or the safety net trips).
  const leaving = played && (timedOut || (ready && logoReady));

  useEffect(() => {
    if (!leaving) return undefined;
    if (!left.current) {
      left.current = true;
      onLeave?.();
    }
    const exit = setTimeout(() => {
      if (finished.current) return;
      finished.current = true;
      onDone?.();
    }, reduced.current ? REDUCED_EXIT_MS : EXIT_MS);
    return () => clearTimeout(exit);
  }, [leaving, onLeave, onDone]);

  return createPortal(
    <div className={`pll${leaving ? ' is-leaving' : ''}`} role="status" aria-live="polite" aria-busy={!leaving}>
      <div className="pll-backdrop" aria-hidden="true" />
      <div className="pll-inner">
        <BrandMark logo={logo} onReady={() => setLogoReady(true)} />
        <div className="pll-text">
          <h1>{school}</h1>
          <i className="pll-rule" aria-hidden="true" />
          <span>{tagline}</span>
        </div>
        <div className="pll-status">
          <div className="pll-line" aria-hidden="true">
            <i />
          </div>
          <p>{MESSAGE[role] || 'Preparing your dashboard...'}</p>
        </div>
      </div>
    </div>,
    document.body,
  );
}
