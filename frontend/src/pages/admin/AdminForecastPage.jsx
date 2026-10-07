import { useEffect, useState } from 'react';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import BasisTag from '../../components/ForecastCharts/BasisTag';
import ProgramBars from '../../components/ForecastCharts/ProgramBars';
import WeeklyChart from '../../components/ForecastCharts/WeeklyChart';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchGrade11Forecast, retrainForecast, saveRetentionRate } from '../../services/adminService';
import { forecastStats } from '../../utils/forecastStats';
import './AdminForecastPage.css';

// trend_status from the server -> the tag shown for a program's next intake.
const STATUS_TAG = { confident: 'forecast', low_confidence: 'low_confidence', untested: 'untested', locked: 'locked' };

function percent(value) {
  return value === null || value === undefined ? '—' : `${Number(value)}%`;
}

function Tile({ label, value, basis, basisLabel, note }) {
  return (
    <article className="card fc-tile">
      <span className="fc-tile-label">{label}</span>
      <strong>{value}</strong>
      <BasisTag kind={basis} label={basisLabel} />
      {note ? <small>{note}</small> : null}
    </article>
  );
}

function Panel({ title, basis, basisLabel, children }) {
  return (
    <section className="card fc-panel">
      <header className="fc-panel-head">
        <h2 className="desk-title">
          <LineMark name="forecast" />
          {title}
        </h2>
        {basis ? <BasisTag kind={basis} label={basisLabel} /> : null}
      </header>
      {children}
    </section>
  );
}

export default function AdminForecastPage() {
  const confirm = useConfirm();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [retention, setRetention] = useState('');

  useEffect(() => {
    fetchGrade11Forecast()
      .then((payload) => {
        setData(payload);
        setRetention(String(Number(payload.retention_rate)));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function run(kind, request) {
    setBusy(kind);
    setError('');
    try {
      const payload = await request();
      setData(payload);
      setRetention(String(Number(payload.retention_rate)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function handleRetrain() {
    const answer = await confirm({
      title: 'Retrain the trend model?',
      body: 'It reads completed school years only and saves a new model version. No student record changes. The retrain is recorded in the audit log.',
      confirmLabel: 'Retrain',
    });
    if (answer) await run('retrain', retrainForecast);
  }

  async function handleRetention(event) {
    event.preventDefault();
    const next = Number(retention);
    if (!Number.isFinite(next) || next < 0 || next > 100) {
      setError('Enter a retention rate from 0 to 100.');
      return;
    }
    const answer = await confirm({
      title: `Set the retention rate to ${next}%?`,
      body: 'It is an assumption about how many approved Grade 11 students continue to Grade 12. Only the Grade 12 estimate changes, and the change is recorded in the audit log.',
      confirmLabel: 'Save rate',
      facts: [
        { label: 'Now', value: percent(data.retention_rate) },
        { label: 'New', value: `${next}%` },
      ],
    });
    if (answer) await run('retention', () => saveRetentionRate(next));
  }

  if (loading) return <Loading label="Loading planning…" />;
  if (!data) return <p className="alert alert-error">{error || 'Planning could not be loaded.'}</p>;

  const stats = forecastStats(data);
  const { trend, model, selection } = stats;
  const ready = trend.status === 'ready';
  const evaluation = model?.evaluation;
  const nextIntake = stats.clusters.reduce((sum, row) => sum + (row.next_intake || 0), 0);
  const trends = stats.clusters.filter((row) => row.projected !== null).length;
  const slots = Array.from({ length: trend.required_years }, (_, index) => trend.completed_labels[index] || null);

  return (
    <div className="fc-page desk">
      <PageHead kicker="Planning" title="Grade 11 forecast" icon="forecast">
        <p>
          Live counts for {stats.year || 'the current year'}, the Grade 12 estimate and the Grade 11 intake for{' '}
          {stats.nextYear || 'next year'}. Every number says what it is based on.
        </p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {stats.demo || trend.synthetic ? (
        <p className="fc-demo" role="note">
          <BasisTag kind="demo" />
          {trend.synthetic
            ? 'The trend was trained on invented history from the demo seed. Nothing here describes real students.'
            : 'This is the demo environment. Synthetic history may appear after the demo seed runs.'}
        </p>
      ) : null}

      {/* 1. Model status */}
      <section className="card fc-status" aria-label="Trend model status">
        <div className="fc-status-main">
          <span className="fc-kicker">Trend model</span>
          <strong>{ready ? 'Ready' : 'Not ready · estimate shown'}</strong>
          <BasisTag kind={ready ? 'forecast' : 'locked'} label={ready ? 'Model forecast active' : 'Trend locked'} />
        </div>
        <div className="fc-slots">
          <div className="fc-slot-row">
            {slots.map((label, index) => (
              <span key={label || index} className={`fc-slot${label ? ' is-done' : ''}`}>
                <b>{label ? '✓ ' : ''}Year {index + 1}</b>
                {label || 'waiting'}
              </span>
            ))}
          </div>
          <small>
            {trend.completed_years} of {trend.required_years} completed years
            {trend.curriculum ? ` under ${trend.curriculum.name}` : ''}
          </small>
        </div>
        <div className="fc-status-side">
          <p>
            {ready && model
              ? `Last trained ${new Date(model.trained_at).toLocaleString()} · v${model.version}`
              : trend.unlock_note || stats.readyReason}
          </p>
          {model?.stale ? <p className="fc-warn">School years were archived or restored since the last training.</p> : null}
          <button className="btn btn-secondary" type="button" disabled={Boolean(busy)} onClick={handleRetrain}>
            {busy === 'retrain' ? 'Retraining…' : 'Retrain'}
          </button>
        </div>
      </section>

      {/* 2. Headline numbers */}
      <div className="fc-tiles">
        <Tile label="Grade 11 applicants" value={stats.appliedTotal} basis="live" note={`${stats.year}, rejected not counted`} />
        <Tile label="Approved" value={stats.total} basis="live" />
        <Tile label="Approval rate" value={percent(stats.approvalRate)} basis="live" />
        <Tile label="Grade 12 sections next year" value={stats.grade12Sections} basis="retention" note={`At ${percent(stats.retention)} retention`} />
        <Tile
          label="Grade 11 sections next year"
          value={stats.grade11Sections}
          basis={trends ? 'forecast' : 'estimate'}
          note={`${stats.typicalCapacity} students per section`}
        />
      </div>

      <div className="fc-duo">
        {/* 3. Applicants by program */}
        <Panel title="Applicants by program" basis="observed">
          <ProgramBars rows={stats.clusters} />
          <div className="admin-staff-table-wrap">
            <table className="admin-staff-table fc-numbers">
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Applied</th>
                  <th>Approved</th>
                  <th>Approval rate</th>
                </tr>
              </thead>
              <tbody>
                {stats.clusters.map((row) => (
                  <tr key={row.code}>
                    <td>{row.code}</td>
                    <td>{row.applied}</td>
                    <td>{row.count}</td>
                    <td>{percent(row.approval_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* 4. Registrations over time */}
        <Panel title="Registrations over time" basis="live" basisLabel="Live data · weekly total">
          <WeeklyChart weeks={stats.weekly} />
        </Panel>
      </div>

      <div className="fc-duo">
        {/* 5. Grade 12 next year */}
        <Panel title={`Grade 12 in ${stats.nextYear || 'next year'}`} basis="retention">
          <form className="fc-retention" onSubmit={handleRetention}>
            <label htmlFor="fc-retention">Retention rate</label>
            <input
              id="fc-retention"
              type="number"
              min="0"
              max="100"
              step="0.5"
              value={retention}
              onChange={(event) => setRetention(event.target.value)}
            />
            <span>%</span>
            <button className="btn btn-secondary" type="submit" disabled={Boolean(busy) || Number(retention) === Number(stats.retention)}>
              {busy === 'retention' ? 'Saving…' : 'Save'}
            </button>
            <small>An assumption you set, not a measurement. It can be measured once a full Grade 12 year exists.</small>
          </form>
          <div className="admin-staff-table-wrap">
            <table className="admin-staff-table fc-numbers">
              <thead>
                <tr>
                  <th>From Grade 11</th>
                  <th>Approved</th>
                  <th>Grade 12 program</th>
                  <th>Expected</th>
                  <th>Sections</th>
                </tr>
              </thead>
              <tbody>
                {stats.strands.length ? (
                  stats.strands.map((row) => (
                    <tr key={row.code}>
                      <td>{row.from_codes.join(', ')}</td>
                      <td>{row.count}</td>
                      <td>
                        {row.code}
                        {row.ready ? '' : ' · set up needed'}
                      </td>
                      <td>{row.expected}</td>
                      <td>{row.sections_needed}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5}>Set "Leads to" on each Grade 11 program to plan Grade 12.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {stats.plan.warnings.length ? (
            <ul className="fc-warnings">
              {stats.plan.warnings.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </Panel>

        {/* 6. Grade 11 next intake */}
        <Panel title={`Grade 11 intake in ${stats.nextYear || 'next year'}`} basis={trends ? 'forecast' : 'estimate'}>
          {ready ? null : (
            <p className="fc-locked">
              <BasisTag kind="locked" />
              {trend.unlock_note || 'Not enough completed years yet.'} Until then each program shows an estimate, not a forecast.
            </p>
          )}
          <div className="admin-staff-table-wrap">
            <table className="admin-staff-table fc-numbers">
              <thead>
                <tr>
                  <th>Program</th>
                  <th>This year</th>
                  <th>Next year</th>
                  <th>Sections</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {stats.clusters.map((row) => (
                  <tr key={row.code}>
                    <td>{row.code}</td>
                    <td>{row.applied}</td>
                    <td>
                      {row.next_intake}
                      {row.next_intake_note ? <small className="fc-note">{row.next_intake_note}</small> : null}
                      {row.direction ? <small className="fc-note">{row.direction}</small> : null}
                    </td>
                    <td>{row.sections_needed}</td>
                    <td>
                      <BasisTag kind={row.projected === null ? 'estimate' : STATUS_TAG[row.trend_status]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {evaluation?.evaluated ? (
            <p className="fc-note-line">
              Tested forward in time on {evaluation.tests} year{evaluation.tests === 1 ? '' : 's'}: typical miss {evaluation.rmse} for the
              trend, {evaluation.baseline_rmse} for "same as last year". {evaluation.note}
            </p>
          ) : null}
        </Panel>
      </div>

      {/* 7. How this was computed */}
      <section className="card fc-panel" aria-label="How this was computed">
        <header className="fc-panel-head">
          <h2 className="desk-title">
            <LineMark name="forecast" />
            How this was computed
          </h2>
        </header>
        <ol className="fc-kdd">
          <li>
            <b>Selection</b>
            <span>
              {selection.records_read ?? 0} registrations read · {trend.completed_years + (trend.other_curriculum_years || 0)} completed years
            </span>
          </li>
          <li>
            <b>Preprocessing</b>
            <span>
              {selection.rejected_excluded ?? 0} rejected left out · {trend.other_curriculum_years || 0} years under another curriculum left out
              {selection.missing_timestamp ? ` · ${selection.missing_timestamp} without a date` : ''}
            </span>
          </li>
          <li>
            <b>Transformation</b>
            <span>
              {stats.clusters.length} programs · {stats.weekly.length} weeks · retention {percent(stats.retention)}
            </span>
          </li>
          <li>
            <b>Data mining</b>
            <span>{trends ? `${trends} LinearRegression trend${trends === 1 ? '' : 's'}` : 'Not run: the trend is locked'}</span>
          </li>
          <li>
            <b>Evaluation</b>
            <span>
              {evaluation?.evaluated
                ? `Forward test: ${evaluation.rmse} vs ${evaluation.baseline_rmse} for same as last year`
                : evaluation?.reason || 'Not run yet'}
            </span>
          </li>
          <li>
            <b>Knowledge</b>
            <span>
              {nextIntake} Grade 11 and {stats.grade12Expected} Grade 12 students expected ·{' '}
              {stats.grade11Sections + stats.grade12Sections} sections
            </span>
          </li>
        </ol>
      </section>
    </div>
  );
}
