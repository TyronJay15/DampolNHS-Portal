import { useEffect, useState } from 'react';
import { useProposal } from '../../../components/Access/proposalContext';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import FieldLabel from './FieldLabel';
import {
  createAnnouncement,
  deleteAnnouncement,
  deleteCmsPhoto,
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
  publish_to: '',
  is_published: false,
};

// Where a published post appears. "Both" is the same post in both places, not a copy.
const PUBLISH_TO = [
  { value: 'website', label: 'Website', help: 'Display on the public school website.' },
  { value: 'dashboard', label: 'Dashboard', help: 'Display inside the school portal dashboard.' },
  { value: 'both', label: 'Both', help: 'Display in both locations.' },
];
const PLACES = { website: 'the public website', dashboard: 'the portal dashboards', both: 'the public website and the portal dashboards' };

// What the post's card says about where it shows. Dashboards list upcoming events only, so dashboard news shows nowhere.
function placement(row) {
  if (!row.is_published) return { text: 'Draft', draft: true };
  if (row.kind !== 'event' && row.publish_to === 'dashboard') return { text: 'Not shown: dashboards list events only', draft: true };
  if (row.kind !== 'event' || row.publish_to === 'website') return { text: 'On website', draft: false };
  return { text: row.publish_to === 'both' ? 'On dashboards and website' : 'On dashboards', draft: false };
}

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
  const confirm = useConfirm();
  // Set when someone tagged to post news opens this page: every change becomes a request to the Admin.
  const proposal = useProposal();
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

  // Proposal mode: send the change to the Admin; resolves to true when it was submitted.
  async function propose(payload, title, warning) {
    setError('');
    setMessage('');
    try {
      const sent = await proposal.propose(payload, { title, warning });
      if (sent) setMessage('Sent to the Admin for approval. Follow it under My access.');
      return Boolean(sent);
    } catch (err) {
      setError(err.message);
      return false;
    }
  }

  async function handleCreate(event) {
    event.preventDefault();
    if (proposal) {
      const kind = form.kind === 'event' ? 'event' : 'announcement';
      const sent = await propose(
        { action: 'create', fields: announcementPayload(form) },
        `Propose this ${kind}${form.is_published ? ' for publishing' : ' as a draft'}?`,
      );
      if (sent) setForm(EMPTY);
      return;
    }
    if (form.is_published) {
      const answer = await confirm({
        title: `Publish this ${form.kind === 'event' ? 'event' : 'announcement'}?`,
        body: `It appears on ${PLACES[form.publish_to]} as soon as you confirm.`,
        confirmLabel: 'Publish',
      });
      if (!answer) return;
    }
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
    const publishing = !row.is_published;
    if (proposal) {
      return propose(
        { action: 'update', announcement: row.id, fields: { is_published: publishing } },
        `Propose ${publishing ? 'publishing' : 'unpublishing'} "${row.title}"?`,
      );
    }
    const answer = await confirm({
      title: publishing ? `Publish "${row.title}"?` : `Unpublish "${row.title}"?`,
      body: publishing
        ? `It appears on ${PLACES[row.publish_to]} as soon as you confirm.`
        : `It is removed from ${PLACES[row.publish_to]} but stays here as a draft.`,
      confirmLabel: publishing ? 'Publish' : 'Unpublish',
      tone: publishing ? 'standard' : 'warning',
    });
    if (!answer) return;
    setError('');
    try {
      await updateAnnouncement(row.id, { is_published: !row.is_published });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function changePublishTo(row, publishTo) {
    if (publishTo === row.publish_to) return;
    if (proposal) {
      return propose(
        { action: 'update', announcement: row.id, fields: { publish_to: publishTo } },
        `Propose publishing "${row.title}" to ${PLACES[publishTo]}?`,
      );
    }
    setError('');
    try {
      await updateAnnouncement(row.id, { publish_to: publishTo });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function savePhoto(row, image) {
    if (proposal) {
      const sent = await propose(
        { action: 'update', announcement: row.id, fields: { image } },
        `Propose a new photo for "${row.title}"?`,
      );
      // A cancelled proposal leaves the just-uploaded photo unused, so it is removed again.
      if (!sent && image) await deleteCmsPhoto(image).catch(() => {});
      return;
    }
    setError('');
    try {
      await updateAnnouncement(row.id, { image });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(row) {
    if (proposal) {
      return propose(
        { action: 'delete', announcement: row.id },
        `Propose deleting "${row.title}"?`,
        'If the Admin approves, the post is removed permanently.',
      );
    }
    const answer = await confirm({
      title: `Delete "${row.title}"?`,
      body: 'It is removed from the website and from this list permanently. This cannot be undone.',
      confirmLabel: 'Delete',
      tone: 'danger',
    });
    if (!answer) return;
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
        <span className={`cms-chip${placement(row).draft ? ' is-draft' : ''}`}>{placement(row).text}</span>
        <label className="form-field cms-publish-to">
          <FieldLabel>Publish to</FieldLabel>
          <select value={row.publish_to} onChange={(event) => changePublishTo(row, event.target.value)}>
            {PUBLISH_TO.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <p>{row.body}</p>
        <div className="cms-news-actions">
          <button className="btn" type="button" onClick={() => togglePublish(row)}>
            {proposal
              ? `Propose ${row.is_published ? 'unpublish' : 'publish'}`
              : row.is_published
                ? 'Unpublish'
                : 'Publish'}
          </button>
          <button className="btn btn-danger" type="button" onClick={() => remove(row)}>
            {proposal ? 'Propose delete' : 'Delete'}
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
            Choose where each post appears. An upcoming event needs a date. Dashboards list upcoming events only.
          </p>
          <label className="form-field">
            <FieldLabel>Title</FieldLabel>
            <input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="form-field">
            <FieldLabel>Type</FieldLabel>
            <select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}>
              <option value="news">News</option>
              <option value="event">Upcoming event</option>
            </select>
          </label>
          <label className="form-field">
            <FieldLabel>Publish to</FieldLabel>
            <select required value={form.publish_to} onChange={(event) => setForm({ ...form, publish_to: event.target.value })}>
              <option value="" disabled>
                Choose where it appears
              </option>
              {PUBLISH_TO.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} — {option.help}
                </option>
              ))}
            </select>
            {form.kind !== 'event' && form.publish_to && form.publish_to !== 'website' ? (
              <span className="admin-meta">Dashboards list upcoming events only, so news shows on the website alone.</span>
            ) : null}
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
              {proposal ? 'Submit for approval' : 'Add announcement'}
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
                News
              </h3>
              {news.map(renderRow)}
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
