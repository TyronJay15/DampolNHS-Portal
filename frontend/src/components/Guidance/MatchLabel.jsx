import { LABELS } from './guidanceText';

// The label is shown with a symbol and words as well as color, so it never depends on color alone.
export default function MatchLabel({ label }) {
  const entry = LABELS[label] || LABELS.limited;
  return (
    <span className={`gd-label is-${LABELS[label] ? label : 'limited'}`}>
      <span aria-hidden="true">{entry.symbol}</span>
      {entry.text}
    </span>
  );
}
