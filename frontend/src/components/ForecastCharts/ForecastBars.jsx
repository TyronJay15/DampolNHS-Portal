import LineMark from '../LineMark/LineMark';
import { shareOf } from '../../utils/forecastStats';
import './ForecastBars.css';

export default function ForecastBars({ rows, total, empty }) {
  if (!rows?.length) return <p className="forecast-empty">{empty || 'No forecast data yet.'}</p>;

  return (
    <ul className="forecast-bars">
      {rows.map((row, index) => {
        const pct = shareOf(row.count, total);
        return (
          <li key={row.code} style={{ '--delay': `${index * 70}ms`, '--fill': `${pct}%` }}>
            <div className="forecast-bars-meta">
              <strong className="desk-line">
                <LineMark name="forecast" size={14} />
                {row.code}
              </strong>
              <span>
                {row.count} · {pct}%
              </span>
            </div>
            <div className="forecast-bars-track" title={`${row.name}: ${row.count} students`}>
              <i />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
