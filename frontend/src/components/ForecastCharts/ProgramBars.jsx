import './PlanningCharts.css';

/** Applied and approved per program on one scale: the light bar is applied, the dark bar inside it approved. */
export default function ProgramBars({ rows }) {
  const max = Math.max(1, ...rows.map((row) => row.applied));
  if (!rows.some((row) => row.applied)) {
    return <p className="fc-empty">Program counts appear after the first Grade 11 applications.</p>;
  }
  return (
    <ul className="fc-bars">
      {rows.map((row) => (
        <li key={row.code} title={`${row.name}: ${row.applied} applied, ${row.count} approved`}>
          <div className="fc-bars-meta">
            <strong>{row.code}</strong>
            <span>
              {row.applied} applied · {row.count} approved
            </span>
          </div>
          <div className="fc-bars-track" aria-hidden="true">
            <i className="is-applied" style={{ width: `${(row.applied / max) * 100}%` }} />
            <i className="is-approved" style={{ width: `${(row.count / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
