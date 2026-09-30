import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import ForecastBars from '../../components/ForecastCharts/ForecastBars';
import { fetchGrade11Forecast, retrainForecast } from '../../services/adminService';
import { forecastStats } from '../../utils/forecastStats';
import './AdminHome.css';

function fill(row) {
  return row.capacity ? `${row.placed} / ${row.capacity}` : `${row.placed}`;
}

export default function AdminForecastPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);

  useEffect(() => {
    fetchGrade11Forecast()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function retrain() {
    setTraining(true);
    setError('');
    try {
      setData(await retrainForecast());
    } catch (err) {
      setError(err.message);
    } finally {
      setTraining(false);
    }
  }

  if (loading) return <Loading label="Loading forecast…" />;

  const stats = forecastStats(data);
  const evaluation = stats.model?.evaluation;
  const target = stats.plan.grade12_curriculum;

  return (
    <div className="forecast-page desk">
      <PageHead kicker="Planning" title="Grade 11 forecast" icon="forecast">
        <p>
          Which Grade 11 clusters students choose in {stats.year || 'the current year'}
          {stats.curriculum ? ` (${stats.curriculum.name})` : ''}, and what {stats.nextYear || 'next year'} needs:
          Grade 12 sections for students moving up, and Grade 11 sections for the next intake.
        </p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="admin-stats">
        <article className="admin-stat is-ok">
          <span className="desk-stat-top">
            <DeskMark name="user" size={16} />
            Grade 11 applicants
          </span>
          <strong>{stats.appliedTotal}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="forecast" size={16} />
            Most chosen cluster
          </span>
          <strong>{stats.favored ? `${stats.favored.code} · ${stats.favored.share}%` : '—'}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="year" size={16} />
            Planning for
          </span>
          <strong>{stats.nextYear || '—'}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="forecast" size={16} />
            Next intake from
          </span>
          <strong>{stats.ready ? `Trend v${stats.model?.version ?? ''}` : 'This year’s count'}</strong>
        </article>
      </div>

      <section className="card forecast-page-card">
        <h2 className="desk-title">
          <LineMark name="forecast" />
          This year · Grade 11 clusters (observed)
        </h2>
        <ForecastBars
          rows={stats.appliedClusters}
          total={stats.appliedTotal}
          empty="Register Grade 11 students to see which clusters attract applicants."
        />
        <div className="admin-staff-table-wrap">
          <table className="admin-staff-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Cluster</th>
                <th>Applied</th>
                <th>Approved</th>
                <th>Share</th>
                <th>Placed / capacity</th>
                <th>Sections</th>
              </tr>
            </thead>
            <tbody>
              {stats.clusters.length ? (
                stats.clusters.map((row) => (
                  <tr key={row.code}>
                    <td>{row.rank}</td>
                    <td>
                      {row.code} — {row.name}
                    </td>
                    <td>{row.applied}</td>
                    <td>{row.count}</td>
                    <td>{row.share}%</td>
                    <td>{fill(row)}</td>
                    <td>{row.sections.length ? row.sections.map((item) => `${item.name} (${fill(item)})`).join(', ') : 'None yet'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7}>No Grade 11 clusters yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card forecast-page-card">
        <h2 className="desk-title">
          <LineMark name="forecast" />
          {stats.nextYear || 'Next year'} plan
        </h2>
        <p className="desk-empty">
          Grade 12 will follow {target ? target.name : 'a curriculum that is not set yet'}
          {stats.plan.grade12_curriculum_set ? ' (set on the School year page)' : ' (full implementation)'}. Sections
          are counted at {stats.typicalCapacity} students each, this year’s typical capacity.
        </p>
        {stats.plan.warnings.length ? (
          <div className="alert alert-info">
            <strong>Before next school year</strong>
            <ul>
              {stats.plan.warnings.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="forecast-page-grid">
          <div className="admin-staff-table-wrap">
            <h3>Grade 12 · students moving up (estimated)</h3>
            <table className="admin-staff-table">
              <thead>
                <tr>
                  <th>Grade 12 program</th>
                  <th>Students</th>
                  <th>Sections</th>
                  <th>Ready</th>
                </tr>
              </thead>
              <tbody>
                {stats.strands.length ? (
                  stats.strands.map((row) => (
                    <tr key={row.code}>
                      <td>
                        {row.code} — {row.name}
                      </td>
                      <td>{row.count}</td>
                      <td>{row.sections_needed}</td>
                      <td>{row.ready ? 'Yes' : 'Set up needed'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4}>Set “Leads to” on each Grade 11 program to plan Grade 12.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="admin-staff-table-wrap">
            <h3>Grade 11 · next intake ({stats.ready ? 'forecast' : 'estimate'})</h3>
            <table className="admin-staff-table">
              <thead>
                <tr>
                  <th>Cluster</th>
                  <th>Expected</th>
                  <th>Sections</th>
                </tr>
              </thead>
              <tbody>
                {stats.clusters.map((row) => (
                  <tr key={row.code}>
                    <td>{row.code}</td>
                    <td>
                      {row.next_intake}
                      {row.next_intake_basis === 'estimate' ? ' (same as this year)' : ''}
                    </td>
                    <td>{row.sections_needed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {stats.readyReason ? <p className="desk-empty">{stats.readyReason}</p> : null}
            {evaluation ? (
              <p className="desk-empty">
                {evaluation.evaluated
                  ? `Held-out check on ${evaluation.programs} program(s): MAE ${evaluation.mae}, RMSE ${evaluation.rmse}.`
                  : evaluation.reason}
              </p>
            ) : null}
            {stats.model?.stale ? (
              <p className="alert alert-info">School years were archived or restored after the last training.</p>
            ) : null}
            <p className="desk-empty">
              {stats.model
                ? `Trend model v${stats.model.version}, trained ${new Date(stats.model.trained_at).toLocaleDateString()}.`
                : 'No trend model trained yet.'}{' '}
              <button className="btn btn-secondary" type="button" disabled={training} onClick={retrain}>
                {training ? 'Retraining…' : 'Retrain'}
              </button>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
