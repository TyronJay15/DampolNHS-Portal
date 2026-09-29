import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import ForecastBars from '../../components/ForecastCharts/ForecastBars';
import { fetchGrade11Forecast } from '../../services/adminService';
import { forecastStats } from '../../utils/forecastStats';
import './AdminHome.css';

export default function AdminForecastPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGrade11Forecast()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading forecast…" />;

  const stats = forecastStats(data);

  return (
    <div className="forecast-page desk">
      <PageHead kicker="Records" title="Grade 11 forecast" icon="forecast">
        <p>
          New SHS applications by cluster for {stats.year || 'the current year'}. Linear Regression
          trains after three intakes. The old Grade 12 map stays as a transition note.
        </p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="admin-stats">
        <article className="admin-stat is-ok">
          <span className="desk-stat-top">
            <DeskMark name="user" size={16} />
            Grade 11 approved
          </span>
          <strong>{stats.total}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="year" size={16} />
            Projected year
          </span>
          <strong>{stats.nextYear || '—'}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="forecast" size={16} />
            Most applied
          </span>
          <strong>
            {stats.mostApplied
              ? `${stats.mostApplied.code} · ${stats.mostApplied.applied}`
              : stats.largest
                ? `${stats.largest.code} · ${stats.largest.applied ?? stats.largest.count}`
                : '—'}
          </strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="forecast" size={16} />
            Model
          </span>
          <strong>{stats.ready ? 'Linear Regression' : 'Counts'}</strong>
        </article>
      </div>

      <div className="forecast-page-grid">
        <section className="card forecast-page-card">
          <h2 className="desk-title">
            <LineMark name="forecast" />
            This year · Grade 11 clusters
          </h2>
          <ForecastBars
            rows={stats.clusters.map((row) => ({ ...row, count: row.applied ?? row.count }))}
            total={stats.clusters.reduce((sum, row) => sum + Number(row.applied ?? row.count ?? 0), 0)}
            empty="Register Grade 11 students to see which new clusters attract applicants."
          />
          {stats.readyReason ? <p className="desk-empty">{stats.readyReason}</p> : null}
        </section>
        <section className="card forecast-page-card">
          <h2 className="desk-title">
            <LineMark name="forecast" />
            Next year · Grade 12 strands
          </h2>
          <ForecastBars rows={stats.strands} total={stats.total} empty="Projected strand counts appear after Grade 11 approvals." />
        </section>
      </div>

      <div className="card admin-staff-table-wrap">
        <table className="admin-staff-table">
          <thead>
            <tr>
              <th>Grade 11 cluster</th>
              <th>Applied</th>
              <th>Approved</th>
              <th>Next intake</th>
              <th>Grade 12 note</th>
            </tr>
          </thead>
          <tbody>
            {stats.clusters.length ? (
              stats.clusters.map((row) => (
                <tr key={row.code}>
                  <td>
                    {row.code} — {row.name}
                  </td>
                  <td>{row.applied ?? row.count}</td>
                  <td>{row.count}</td>
                  <td>{row.projected == null ? '—' : row.projected}</td>
                  <td>
                    {row.grade12_code} — {row.grade12_name}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>No Grade 11 cluster counts yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
