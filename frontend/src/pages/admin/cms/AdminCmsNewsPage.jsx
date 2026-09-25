import { useEffect, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import FieldLabel from './FieldLabel';
import {
  createAnnouncement,
  deleteAnnouncement,
  fetchAnnouncementsAdmin,
  updateAnnouncement,
} from '../../../services/cmsService';
import CmsPhotoField from './CmsPhotoField';
import './AdminCms.css';

const EMPTY = {
  title: '',
  body: '',
  image: '',
  category: '',
  kind: 'news',
  event_date: '',
  event_end_date: '',
  location: '',
  is_published: false,
};

function eventMeta(row) {
  if (row.kind !== 'event') return row.category || 'General';
  const when = row.event_date || 'Needs a date';
  return [when, row.location, row.category || 'Event'].filter(Boolean).join(' · ');
}

function announcementPayload(form) {
  const isEvent = form.kind === 'event';
  return {
    ...form,
    event_date: isEvent && form.event_date ? form.event_date : null,
    event_end_date: isEvent && form.event_end_date ? form.event_end_date : null,
    location: isEvent ? form.location : '',
  };
}

export default function AdminCmsNewsPage() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load() {
    setRows(await fetchAnnouncementsAdmin());
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    setError('');
    try {
      await createAnnouncement(announcementPayload(form));
      setForm(EMPTY);
      setMessage('Announcement saved.');
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function togglePublish(row) {
    setError('');
    try {
      await updateAnnouncement(row.id, { is_published: !row.is_published });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function savePhoto(row, image) {
    setError('');
    try {
      await updateAnnouncement(row.id, { image });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(row) {
    setError('');
    try {
      await deleteAnnouncement(row.id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading label="Loading news…" />;

  const events = rows.filter((row) => row.kind === 'event');
  const news = rows.filter((row) => row.kind !== 'event');

  function renderRow(row) {
    return (
      <article className="card cms-card cms-news-item" key={row.id}>
        <CmsPhotoField label="Photo" value={row.image} onChange={(image) => savePhoto(row, image)} />
        <h3 className="desk-line">
          <LineMark name={row.kind === 'event' ? 'year' : 'bell'} size={14} />
          {row.title}
        </h3>
        <p className="admin-meta">{eventMeta(row)}</p>
        <span className={`cms-chip${row.is_published ? '' : ' is-draft'}`}>
          {row.is_published ? (row.kind === 'event' ? 'On dashboards' : 'On website') : 'Draft'}
        </span>
        <p>{row.body}</p>
        <div className="cms-news-actions">
          <button className="btn" type="button" onClick={() => togglePublish(row)}>
            {row.is_published ? 'Unpublish' : 'Publish'}
          </button>
          <button className="btn btn-danger" type="button" onClick={() => remove(row)}>
            Delete
          </button>
        </div>
      </article>
    );
  }

  return (
    <div>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}
      <div className="cms-news">
        <form className="card cms-card" onSubmit={handleCreate}>
          <h2 className="desk-line">
            <LineMark name="bell" />
            New post
          </h2>
          <p className="admin-meta">
            News stays on the public site. Upcoming events need a date and appear on every dashboard.
          </p>
          <label className="form-field">
            <FieldLabel>Title</FieldLabel>
            <input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="form-field">
            <FieldLabel>Type</FieldLabel>
            <select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}>
              <option value="news">News — public website only</option>
              <option value="event">Upcoming event — dashboards</option>
            </select>
          </label>
          <label className="form-field">
            <FieldLabel>Category</FieldLabel>
            <input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} />
          </label>
          {form.kind === 'event' ? (
            <>
              <div className="cms-grid-2">
                <label className="form-field">
                  <FieldLabel>Event date</FieldLabel>
                  <input
                    type="date"
                    required={form.is_published}
                    value={form.event_date}
                    onChange={(event) => setForm({ ...form, event_date: event.target.value })}
                  />
                </label>
                <label className="form-field">
                  <FieldLabel>End date</FieldLabel>
                  <input
                    type="date"
                    value={form.event_end_date}
                    onChange={(event) => setForm({ ...form, event_end_date: event.target.value })}
                  />
                </label>
              </div>
              <label className="form-field">
                <FieldLabel>Location</FieldLabel>
                <input
                  value={form.location}
                  onChange={(event) => setForm({ ...form, location: event.target.value })}
                />
              </label>
            </>
          ) : null}
          <CmsPhotoField label="Photo" value={form.image} onChange={(image) => setForm({ ...form, image })} />
          <label className="form-field">
            <FieldLabel>Body</FieldLabel>
            <textarea
              required
              rows={5}
              value={form.body}
              onChange={(event) => setForm({ ...form, body: event.target.value })}
            />
          </label>
          <label className="form-field admin-cms-check">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(event) => setForm({ ...form, is_published: event.target.checked })}
            />
            Publish now
          </label>
          <div className="cms-save">
            <button className="btn" type="submit">
              Add announcement
            </button>
          </div>
        </form>

        <div className="cms-news-list">
          {rows.length === 0 ? <p className="admin-meta">No announcements yet.</p> : null}
          {events.length ? (
            <section className="cms-news-group">
              <h3 className="desk-line">
                <LineMark name="year" size={14} />
                Upcoming events
              </h3>
              {events.map(renderRow)}
            </section>
          ) : null}
          {news.length ? (
            <section className="cms-news-group">
              <h3 className="desk-line">
                <LineMark name="bell" size={14} />
                Website news
              </h3>
              {news.map(renderRow)}
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
