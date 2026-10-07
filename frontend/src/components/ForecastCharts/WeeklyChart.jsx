import './PlanningCharts.css';

const W = 520;
const H = 210;
const PAD = { left: 40, right: 54, top: 14, bottom: 30 };

function niceMax(value) {
  if (value <= 5) return 5;
  const step = 10 ** Math.floor(Math.log10(value));
  return Math.ceil(value / step) * step;
}

function shortDate(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/** Valid Grade 11 applications, added up week by week (weeks start on Monday). */
export default function WeeklyChart({ weeks }) {
  if (!weeks.length) return <p className="fc-empty">The weekly line appears after the first Grade 11 application.</p>;
  const top = niceMax(weeks[weeks.length - 1].total);
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const x = (index) => PAD.left + (weeks.length === 1 ? plotW / 2 : (plotW * index) / (weeks.length - 1));
  const y = (value) => PAD.top + plotH - (plotH * value) / top;
  const ticks = [0, top / 2, top];
  const labelEvery = Math.max(1, Math.ceil(weeks.length / 6));
  const points = weeks.map((week, index) => `${x(index)},${y(week.total)}`).join(' ');
  const last = weeks[weeks.length - 1];

  return (
    <>
      <svg className="fc-line" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Valid applications reached ${last.total} by the week of ${shortDate(last.week_start)}`}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className={tick ? 'fc-grid' : 'fc-axis'} x1={PAD.left} x2={W - PAD.right} y1={y(tick)} y2={y(tick)} />
            <text x={PAD.left - 8} y={y(tick) + 4} textAnchor="end">
              {Math.round(tick)}
            </text>
          </g>
        ))}
        {weeks.map((week, index) =>
          index % labelEvery === 0 ? (
            <text key={week.week_start} x={x(index)} y={H - 10} textAnchor="middle">
              {shortDate(week.week_start)}
            </text>
          ) : null,
        )}
        <polygon className="fc-area" points={`${x(0)},${y(0)} ${points} ${x(weeks.length - 1)},${y(0)}`} />
        <polyline className="fc-path" points={points} />
        {weeks.map((week, index) => (
          <circle key={week.week_start} className="fc-dot" cx={x(index)} cy={y(week.total)} r={index === weeks.length - 1 ? 4.5 : 3}>
            <title>{`Week of ${shortDate(week.week_start)}: +${week.added}, ${week.total} in total`}</title>
          </circle>
        ))}
        <text className="fc-end" x={x(weeks.length - 1) + 8} y={y(last.total) + 4}>
          {last.total}
        </text>
      </svg>
      <details className="fc-table">
        <summary>Show the weekly numbers</summary>
        <div className="admin-staff-table-wrap">
          <table className="admin-staff-table">
            <thead>
              <tr>
                <th>Week of</th>
                <th>Added</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {weeks.map((week) => (
                <tr key={week.week_start}>
                  <td>{shortDate(week.week_start)}</td>
                  <td>{week.added}</td>
                  <td>{week.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
