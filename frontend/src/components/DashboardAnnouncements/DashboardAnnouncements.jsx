import { useEffect, useState } from 'react';
import AnnouncementReader from '../AnnouncementReader/AnnouncementReader';
import DeskMark from '../DeskMark/DeskMark';
import { fetchDashboardNews } from '../../services/publicService';
import { formatPostedOn, textPreview } from '../../utils/textPreview';
import './DashboardAnnouncements.css';

const SHOWN = 3;

/** CMS News published to "Dashboard" or "Both". Events stay in Upcoming events; the server does the filtering. */
export default function DashboardAnnouncements() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(null);

  useEffect(() => {
    fetchDashboardNews()
      .then((data) => setRows((Array.isArray(data) ? data : []).slice(0, SHOWN)))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <article className="card desk-tile">
      <h2>
        <span className="desk-title">
          <DeskMark name="bell" size={16} />
          Announcements
        </span>
      </h2>
      {error ? <p className="desk-empty">{error}</p> : null}
      {!error && rows.length === 0 ? <p className="desk-empty">No announcements at this time.</p> : null}
      {rows.length ? (
        <ul className="desk-event-list">
          {rows.map((row) => {
            const preview = textPreview(row.body, 110);
            return (
              <li key={row.id}>
                <button type="button" className="desk-news-open" onClick={() => setOpen(row)}>
                  {row.published_at ? <em>{formatPostedOn(row.published_at)}</em> : null}
                  <strong>{row.title}</strong>
                  {preview.text ? <span>{preview.text}</span> : null}
                  <span className="desk-news-more">Read more</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      <AnnouncementReader item={open} onClose={() => setOpen(null)} />
    </article>
  );
}
