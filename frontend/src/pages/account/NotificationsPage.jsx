import { useEffect, useState } from 'react';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../services/studentService';
import '../student/StudentStudio.css';

function formatWhen(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function NotificationsPage() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchNotifications()
      .then((data) => setRows(data.notifications || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function markOne(row) {
    if (row.is_read || busy) return;
    setBusy(true);
    setError('');
    try {
      const updated = await markNotificationRead(row.id);
      setRows((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function markAll() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await markAllNotificationsRead();
      setRows((current) => current.map((item) => ({ ...item, is_read: true })));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading notifications…" />;

  const unreadCount = rows.filter((row) => !row.is_read).length;
  const visible = filter === 'unread' ? rows.filter((row) => !row.is_read) : rows;

  return (
    <div className="desk student-studio">
      <PageHead kicker="Inbox" title="Notifications" icon="bell">
        <p>School notices for your account. Event reminders, grade workflow, and account changes.</p>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="student-toolbar">
        <div className="student-filters">
          <button
            type="button"
            className={`student-filter${filter === 'all' ? ' is-active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All <em>{rows.length}</em>
          </button>
          <button
            type="button"
            className={`student-filter${filter === 'unread' ? ' is-active' : ''}`}
            onClick={() => setFilter('unread')}
          >
            Unread <em>{unreadCount}</em>
          </button>
        </div>
        {unreadCount ? (
          <button type="button" className="btn btn-secondary" onClick={markAll} disabled={busy}>
            Mark all as read
          </button>
        ) : null}
      </div>

      {visible.length === 0 ? (
        <p className="card student-panel student-empty student-empty-card">
          {rows.length === 0 ? 'No notifications yet.' : 'No unread notifications.'}
        </p>
      ) : (
        <ul className="student-note-list">
          {visible.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                className={`card student-note${row.is_read ? '' : ' is-unread'}`}
                onClick={() => markOne(row)}
              >
                <p className="student-note-when">
                  {formatWhen(row.created_at)}
                  {row.is_read ? null : <em>New</em>}
                </p>
                <h2>
                  <LineMark name="bell" />
                  {row.title}
                </h2>
                <p>{row.body}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
