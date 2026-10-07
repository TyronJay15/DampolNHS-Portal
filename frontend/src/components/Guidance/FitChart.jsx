import { grade } from './guidanceText';

const WIDTH = 520;
const LEFT = 96;
const RIGHT = 24;
const TOP = 10;
const ROW = 36;
const LOW = 50;
const HIGH = 100;
const TICKS = [50, 60, 70, 80, 90, 100];

function x(value) {
  return LEFT + ((WIDTH - LEFT - RIGHT) * (Number(value) - LOW)) / (HIGH - LOW);
}

function clamp(value) {
  return Math.max(LOW, Math.min(HIGH, Number(value)));
}

// The student's grade against what a program's validated profile expects, per skill area.
// rows: [{ key, label, student (or null), expected, benchmark (or null), official }]
export default function FitChart({ rows, title }) {
  if (!rows.length) return <p className="gd-note">This program has no skill profile yet.</p>;
  const height = TOP + ROW * rows.length + 26;
  const summary = rows
    .map((row) => `${row.label}: yours ${row.student === null ? 'not graded yet' : grade(row.student)}, profile ${grade(row.expected)}`)
    .join('; ');
  return (
    <figure className="gd-chart">
      <div className="gd-legend" aria-hidden="true">
        <span>
          <i className="gd-key-dot" />
          Your grade
        </span>
        <span>
          <i className="gd-key-diamond" />
          Profile expects
        </span>
        <span>
          <i className="gd-key-tick" />
          Benchmark
        </span>
      </div>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label={`${title}. ${summary}`}>
        {TICKS.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={TOP} y2={height - 22} stroke="var(--dash-line)" />
            <text x={x(tick)} y={height - 6} textAnchor="middle">
              {tick}
            </text>
          </g>
        ))}
        {rows.map((row, index) => {
          const y = TOP + ROW * index + ROW / 2;
          const expected = x(clamp(row.expected));
          const student = row.student === null ? null : x(clamp(row.student));
          return (
            <g key={row.key}>
              <text x={LEFT - 10} y={y + 4} textAnchor="end">
                {row.label}
              </text>
              {student === null ? null : (
                <line
                  x1={Math.min(student, expected)}
                  x2={Math.max(student, expected)}
                  y1={y}
                  y2={y}
                  stroke="var(--dash-line)"
                  strokeWidth="3"
                />
              )}
              <rect
                x={expected - 5}
                y={y - 5}
                width="10"
                height="10"
                fill="var(--dash-panel)"
                stroke="var(--dash-muted)"
                strokeWidth="2"
                transform={`rotate(45 ${expected} ${y})`}
              />
              {row.benchmark === null ? null : (
                <line
                  x1={x(clamp(row.benchmark))}
                  x2={x(clamp(row.benchmark))}
                  y1={y - 11}
                  y2={y + 11}
                  stroke="var(--dash-ink)"
                  strokeWidth="2.5"
                  strokeDasharray={row.official ? '' : '3 2'}
                />
              )}
              {student === null ? (
                <text x={x(LOW) + 6} y={y + 4}>
                  not graded yet
                </text>
              ) : (
                <>
                  <circle cx={student} cy={y} r="6" fill="var(--dash-green)" stroke="var(--dash-panel)" strokeWidth="2" />
                  <text className="is-value" x={student} y={y - 10} textAnchor="middle">
                    {grade(row.student)}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="gd-note">
        A dashed benchmark is guidance; a solid one is an official requirement with a stated source.
      </figcaption>
    </figure>
  );
}
