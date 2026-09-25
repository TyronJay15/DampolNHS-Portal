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
          Approved Grade 11 clusters for {stats.year || 'the current year'} map to Grade 12 strands
          {stats.nextYear ? ` for ${stats.nextYear}` : ''}. Bars use live registration counts, not estimates.
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
            Largest cluster
          </span>
          <strong>{stats.largest ? `${stats.largest.code} · ${stats.largest.count}` : '—'}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="forecast" size={16} />
            Smallest Grade 12 map
          </span>
          <strong>{stats.smallest ? `${stats.smallest.code} · ${stats.smallest.count}` : '—'}</strong>
        </article>
      </div>

      <div className="forecast-page-grid">
        <section className="card forecast-page-card">
          <h2 className="desk-title">
            <LineMark name="forecast" />
            This year · Grade 11 clusters
          </h2>
          <ForecastBars rows={stats.clusters} total={stats.total} empty="Approve Grade 11 students to see cluster shares." />
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
              <th>Students</th>
              <th>Grade 12 strand</th>
            </tr>
          </thead>
          <tbody>
            {stats.clusters.length ? (
              stats.clusters.map((row) => (
                <tr key={row.code}>
                  <td>
                    {row.code} — {row.name}
                  </td>
                  <td>{row.count}</td>
                  <td>
                    {row.grade12_code} — {row.grade12_name}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3}>No Grade 11 cluster counts yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
