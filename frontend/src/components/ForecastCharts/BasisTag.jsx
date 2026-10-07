import './PlanningCharts.css';

// What a number is based on. The glyph and the words carry the meaning, never the color alone.
const KINDS = {
  live: { glyph: '●', label: 'Live data' },
  observed: { glyph: '●', label: 'Observed' },
  estimate: { glyph: '◇', label: 'Estimate' },
  retention: { glyph: '◇', label: 'Retention-based estimate' },
  forecast: { glyph: '▲', label: 'Model forecast' },
  confident: { glyph: '▲', label: 'Model forecast' },
  low_confidence: { glyph: '⚠', label: 'Low confidence' },
  untested: { glyph: '○', label: 'Not yet tested' },
  locked: { glyph: '⊘', label: 'Trend locked' },
  demo: { glyph: '◆', label: 'Synthetic demo data' },
};

export default function BasisTag({ kind, label }) {
  const item = KINDS[kind] || KINDS.estimate;
  return (
    <span className={`fc-tag is-${kind}`}>
      <span aria-hidden="true">{item.glyph}</span>
      {label || item.label}
    </span>
  );
}
