import { useEffect, useState } from 'react';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fileUrl } from '../../services/api';
import { fetchUpcomingEvents } from '../../services/publicService';
import { formatEventWhen } from '../../utils/textPreview';

export default function EventsPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUpcomingEvents()
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading events…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Campus" title="Upcoming events" icon="year">
        <p>Published events for dashboards. Ordinary news stays on the public website.</p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {!error && rows.length === 0 ? (
        <p className="card desk-tile desk-empty">
          No upcoming events yet. Publish an Upcoming event in CMS News.
        </p>
      ) : null}
      {rows.length ? (
        <div className="desk-event-cards">
          {rows.map((row) => {
            const when = formatEventWhen(row, { long: true });
            return (
              <article key={row.id} className="card desk-tile desk-event-card">
                {row.image ? <img src={fileUrl(row.image)} alt="" /> : null}
                {when ? <p className="desk-kicker">{when}</p> : null}
                <h2>{row.title}</h2>
                {row.location ? <p className="desk-event-place">{row.location}</p> : null}
                {row.body ? <p className="desk-event-body">{row.body}</p> : null}
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
