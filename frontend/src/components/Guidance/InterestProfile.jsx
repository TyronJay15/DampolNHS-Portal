import { scoreWidth } from './guidanceText';

// The six interest scores from the assessment, each the mean of five answers on a 1 to 5 scale.
export default function InterestProfile({ scores }) {
  if (!scores?.length) return <p className="gd-note">Take the interest assessment to see your interest profile.</p>;
  return (
    <div className="gd-interest" role="list">
      {scores.map((row) => (
        <div key={row.type} className="gd-bar-row" role="listitem">
          <span>{row.label}</span>
          <span className="gd-bar" aria-hidden="true">
            <i style={{ width: `${scoreWidth(row.score)}%` }} />
          </span>
          <b>{Number(row.score).toFixed(1)}</b>
        </div>
      ))}
    </div>
  );
}
