import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../services/studentService';
import { NOTIFICATION_FILTERS, categoryLabel, filterNotifications } from '../../utils/auditTrail';
import '../../styles/studio.css';

function formatWhen(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function categoryCount(rows, value) {
  if (value === 'all') return rows.length;
  return rows.filter((row) => row.category === value).length;
}

export default function NotificationsPage() {
  const [rows, setRows] = useState([]);
  const [category, setCategory] = useState('all');
  const [unreadOnly, setUnreadOnly] = useState(false);
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

  const unreadCount = rows.filter((row) => !row.is_read).length;
  const visible = useMemo(
    () => filterNotifications(rows, category, unreadOnly),
    [category, unreadOnly, rows],
  );
  const activeLabel = NOTIFICATION_FILTERS.find((tab) => tab.value === category)?.label || 'All';

  if (loading) return <Loading label="Loading notifications…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Inbox" title="Notifications" icon="bell">
        <p>
          {unreadOnly
            ? `Unread ${activeLabel.toLowerCase()} notices.`
            : `${activeLabel} notices for this account.`}
        </p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{unreadCount} unread</span>
          <span className="studio-chip">{rows.length} total</span>
        </div>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-tabs is-page">
        {NOTIFICATION_FILTERS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            className={category === tab.value ? 'is-active' : ''}
            onClick={() => setCategory(tab.value)}
          >
            {tab.label}
            <em>{categoryCount(rows, tab.value)}</em>
          </button>
        ))}
      </div>

      <div className="studio-actions">
        <button
          type="button"
          className={`btn btn-secondary${unreadOnly ? ' is-on' : ''}`}
          onClick={() => setUnreadOnly((current) => !current)}
        >
          {unreadOnly ? 'Showing unread' : 'Unread only'}
        </button>
        {unreadCount ? (
          <button className="btn" type="button" onClick={markAll} disabled={busy}>
            Mark all as read
          </button>
        ) : null}
      </div>

      <section className="card studio-panel">
        <h2>
          <LineMark name="bell" />
          {activeLabel}
        </h2>
        {visible.length === 0 ? (
          <p className="studio-empty">
            {rows.length === 0 ? 'No notifications yet.' : 'No notifications match that filter.'}
          </p>
        ) : (
          <div className="studio-inbox">
            {visible.map((row) => (
              <article
                key={row.id}
                className={`studio-inbox-row${row.is_read ? '' : ' is-unread'}${row.level ? ` is-${row.level}` : ''}`}
              >
                <button type="button" className="studio-inbox-copy" onClick={() => markOne(row)}>
                  <p className="studio-inbox-meta">
                    <span className="studio-chip">{categoryLabel(row.category)}</span>
                    <span>{formatWhen(row.created_at)}</span>
                    {row.is_read ? null : <em>New</em>}
                  </p>
                  <h3>
                    <LineMark name="bell" size={14} />
                    {row.title}
                  </h3>
                  <p>{row.body}</p>
                </button>
                {row.action_path ? (
                  <div className="studio-actions">
                    <Link className="btn btn-secondary" to={row.action_path}>
                      Open
                    </Link>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
