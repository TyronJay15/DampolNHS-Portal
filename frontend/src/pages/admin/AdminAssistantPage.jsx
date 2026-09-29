import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchAssistantStats } from '../../services/adminService';
import './AdminHome.css';

function formatWhen(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function AdminAssistantPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAssistantStats()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading assistant…" />;

  const intent = data?.intent || {};
  const asked = data?.asked || {};
  const topics = data?.topics || [];
  const recent = data?.recent || [];

  return (
    <div className="desk studio">
      <PageHead kicker="Machine learning" title="Assistant" icon="bell">
        <p>
          The trained topic classifier labels each visitor question. Gemini only phrases a school FAQ
          answer. The key stays on the API.
        </p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="admin-stats">
        <article className="admin-stat is-ok">
          <span className="desk-stat-top">
            <DeskMark name="check" size={16} />
            Intent accuracy
          </span>
          <strong>{intent.ready && intent.accuracy != null ? `${Math.round(intent.accuracy * 100)}%` : '—'}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="user" size={16} />
            Asked this month
          </span>
          <strong>{asked.month || 0}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="bell" size={16} />
            Training rows
          </span>
          <strong>{intent.n_train || 0}</strong>
        </article>
        <article className="admin-stat">
          <span className="desk-stat-top">
            <DeskMark name="year" size={16} />
            Last train
          </span>
          <strong>{intent.trained_at ? new Date(intent.trained_at).toLocaleDateString() : '—'}</strong>
        </article>
      </div>

      <section className="card studio-panel">
        <h2 className="desk-title">
          <LineMark name="forecast" />
          Most asked topics
        </h2>
        {topics.length === 0 ? (
          <p className="desk-empty">No visitor questions logged yet.</p>
        ) : (
          <table className="admin-staff-table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Count</th>
                <th>Last asked</th>
              </tr>
            </thead>
            <tbody>
              {topics.map((row) => (
                <tr key={row.topic}>
                  <td>{row.topic}</td>
                  <td>{row.count}</td>
                  <td>{formatWhen(row.last_asked)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card studio-panel">
        <h2 className="desk-title">
          <LineMark name="bell" />
          Recent questions
        </h2>
        {recent.length === 0 ? (
          <p className="desk-empty">Ask the public chatbot to start the log.</p>
        ) : (
          <ul className="desk-event-list">
            {recent.slice(0, 12).map((row) => (
              <li key={row.id}>
                <em>{row.topic}</em>
                <strong>{row.question}</strong>
                <span>
                  {row.source} · {formatWhen(row.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
