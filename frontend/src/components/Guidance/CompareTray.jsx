import { Link } from 'react-router-dom';
import { MAX_COMPARE } from './compareStore';

export default function CompareTray({ compare, comparePath }) {
  if (!compare.codes.length) return null;
  const ready = compare.codes.length >= 2;
  return (
    <div className="gd-compare-tray" role="region" aria-label="Programs to compare">
      <span>
        {compare.codes.length} of {MAX_COMPARE} programs picked to compare
      </span>
      <div className="gd-actions">
        <button className="btn btn-secondary" type="button" onClick={compare.clear}>
          Clear
        </button>
        {ready ? (
          <Link className="btn" to={`${comparePath}?programs=${compare.codes.join(',')}`}>
            Compare now
          </Link>
        ) : (
          <span className="gd-note">Pick one more program to compare.</span>
        )}
      </div>
    </div>
  );
}
