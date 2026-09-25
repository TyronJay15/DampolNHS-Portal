import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import DeskMark from '../DeskMark/DeskMark';
import { fetchUpcomingEvents } from '../../services/publicService';
import { formatEventWhen, textPreview } from '../../utils/textPreview';

export default function UpcomingEvents({ to }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchUpcomingEvents()
      .then((data) => setRows((Array.isArray(data) ? data : []).slice(0, 3)))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <article className="card desk-tile">
      <h2>
        <span className="desk-title">
          <DeskMark name="year" size={16} />
          Upcoming events
        </span>
        {to ? <Link to={to}>View all</Link> : null}
      </h2>
      {error ? <p className="desk-empty">{error}</p> : null}
      {!error && rows.length === 0 ? (
        <p className="desk-empty">Publish an Upcoming event in CMS News. Ordinary news stays on the public site.</p>
      ) : null}
      {rows.length ? (
        <ul className="desk-event-list">
          {rows.map((row) => {
            const preview = textPreview(row.body, 90);
            return (
              <li key={row.id}>
                <em>{formatEventWhen(row)}</em>
                <strong>{row.title}</strong>
                {row.location ? <span>{row.location}</span> : null}
                {preview.text ? <span>{preview.text}</span> : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </article>
  );
}
