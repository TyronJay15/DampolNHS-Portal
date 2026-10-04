import { useCallback, useEffect, useMemo, useState } from 'react';
import RequestChanges from '../../components/Access/RequestChanges';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import {
  closeAccessTag,
  decideAccessRequest,
  fetchAccessOverview,
  fetchAccessRequests,
  fetchAccessTags,
  grantAccessTag,
} from '../../services/accessService';
import { when } from '../../utils/when';
import './AccessPage.css';

const STATE_LABEL = { active: 'Active', ended: 'Ended', closed: 'Closed' };
const STATUS_CLASS = {
  approved: 'is-approved',
  declined: 'is-wait',
  withdrawn: 'is-wait',
  expired: 'is-wait',
  failed: 'is-progress',
};
const EMPTY_FORM = { activity: '', holder: '', scope: '', ends_on: '', no_end_date: false, note: '' };

// "Tina Cruz (Teacher)": every person is shown with their role.
function withRole(person) {
  return person ? `${person.name} (${person.role_label})` : '—';
}

// The tag form lists people under their role, head teachers first.
function byRole(people) {
  const groups = new Map();
  people.forEach((person) => groups.set(person.role_label, [...(groups.get(person.role_label) || []), person]));
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function shortDate(value) {
  if (!value) return 'No end date';
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' });
}

// The owner's side of access tags: requests waiting for approval, the tags given out, and the history.
export default function AccessPage() {
  const confirm = useConfirm();
  const [tab, setTab] = useState('requests');
  const [overview, setOverview] = useState(null);
  const [inbox, setInbox] = useState([]);
  const [tags, setTags] = useState([]);
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [summary, waiting, given, decided] = await Promise.all([
      fetchAccessOverview(),
      fetchAccessRequests('inbox'),
      fetchAccessTags(),
      fetchAccessRequests('decided'),
    ]);
    setOverview(summary);
    setInbox(waiting);
    setTags(given);
    setHistory(decided);
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  const activity = useMemo(
    () => overview?.owns.find((item) => item.key === form.activity) || null,
    [overview, form.activity],
  );

  if (!overview) return error ? <p className="alert alert-error">{error}</p> : <Loading label="Loading access…" />;

  async function run(key, work, done) {
    setBusy(key);
    setError('');
    setMessage('');
    try {
      const result = await work();
      await load();
      setMessage(done(result));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function approve(row) {
    const answer = await confirm({
      title: 'Approve and apply this request?',
      body: row.summary,
      confirmLabel: 'Approve and apply',
      facts: [
        { label: 'Proposed by', value: withRole(row.requested_by) },
        { label: 'Activity', value: row.activity_label },
      ],
      warning: 'It is checked again and carried out now, as if you did it yourself.',
      note: { label: 'Note', placeholder: 'Optional note for the record' },
    });
    if (!answer) return;
    run(
      `decide-${row.id}`,
      () => decideAccessRequest(row.id, { approve: true, note: answer.note }),
      (result) =>
        result.status === 'failed'
          ? `Approved, but it could not be applied: ${result.result?.error || 'the data changed.'}`
          : 'Approved and applied.',
    );
  }

  async function decline(row) {
    const answer = await confirm({
      title: 'Decline this request?',
      body: row.summary,
      confirmLabel: 'Decline request',
      tone: 'warning',
      note: { label: 'Reason', placeholder: 'Tell them why it was declined', required: true, maxLength: 255 },
    });
    if (!answer) return;
    run(
      `decide-${row.id}`,
      () => decideAccessRequest(row.id, { approve: false, note: answer.note }),
      () => 'Request declined.',
    );
  }

  async function grant(event) {
    event.preventDefault();
    const holder = activity?.holders.find((person) => String(person.id) === form.holder);
    if (!activity || !holder) return;
    const answer = await confirm({
      title: `Tag ${withRole(holder)}?`,
      body: `They can prepare "${activity.label}". Every change they prepare comes to you for approval first.`,
      confirmLabel: 'Tag person',
      facts: [
        {
          label: 'Limited to',
          value: activity.scope_options.find((option) => option.value === form.scope)?.label || activity.scope_all,
        },
        { label: 'Until', value: form.no_end_date ? 'No end date' : shortDate(form.ends_on) },
      ],
    });
    if (!answer) return;
    run(
      'grant',
      () =>
        grantAccessTag({
          activity: form.activity,
          holder: Number(form.holder),
          scope: form.scope,
          ends_on: form.no_end_date ? null : form.ends_on,
          no_end_date: form.no_end_date,
          note: form.note,
        }),
      () => {
        setForm(EMPTY_FORM);
        return `${holder.name} was tagged for ${activity.label}.`;
      },
    );
  }

  async function closeTag(tag) {
    const answer = await confirm({
      title: `Close ${tag.holder.name}'s tag?`,
      body: `They can no longer prepare "${tag.activity_label}".`,
      confirmLabel: 'Close tag',
      tone: 'warning',
      warning: tag.pending ? `${tag.pending} waiting request(s) from this tag will be cancelled.` : undefined,
      note: { label: 'Reason', placeholder: 'Why is this tag closed?', required: true, maxLength: 255 },
    });
    if (!answer) return;
    run(
      `close-${tag.id}`,
      () => closeAccessTag(tag.id, answer.note),
      () => 'Tag closed.',
    );
  }

  const canGrant = activity && form.holder && (form.no_end_date || form.ends_on);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="desk studio">
      <PageHead kicker="Delegation" title="Access" icon="access">
        <p>
          Tag a person to prepare one of your activities. They never change anything directly: each request waits here
          for your approval.
        </p>
      </PageHead>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-tabs acc-tabs" role="tablist">
        {[
          ['requests', `Requests${inbox.length ? ` (${inbox.length})` : ''}`],
          ['tags', 'Tags'],
          ['history', 'History'],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? 'is-active' : ''}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'requests' ? (
        inbox.length === 0 ? (
          <p className="card studio-panel studio-empty">No requests are waiting for your approval.</p>
        ) : (
          <div className="acc-list">
            {inbox.map((row) => (
              <article className="card studio-panel acc-card" key={row.id}>
                <div className="acc-card-main">
                  <span className="studio-chip">{row.activity_label}</span>
                  <h2>{row.summary}</h2>
                  <p className="acc-meta">
                    From {withRole(row.requested_by)} · {row.scope_text} · sent {when(row.created_at)} · expires{' '}
                    {when(row.expires_at)}
                  </p>
                  {row.note ? <blockquote className="acc-note">{row.note}</blockquote> : null}
                  <RequestChanges changes={row.changes} />
                </div>
                <div className="acc-actions">
                  <button
                    className="btn btn-secondary"
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={() => decline(row)}
                  >
                    Decline
                  </button>
                  <button className="btn" type="button" disabled={Boolean(busy)} onClick={() => approve(row)}>
                    {busy === `decide-${row.id}` ? 'Working…' : 'Approve'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )
      ) : null}

      {tab === 'tags' ? (
        <>
          <form className="card studio-panel acc-grant" onSubmit={grant}>
            <h2>
              <LineMark name="access" />
              Tag someone
            </h2>
            <div className="acc-grant-grid">
              <label className="form-field">
                <span>Activity</span>
                <select
                  value={form.activity}
                  onChange={(event) => setForm({ ...EMPTY_FORM, activity: event.target.value })}
                  required
                >
                  <option value="">Choose an activity</option>
                  {overview.owns.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>Person</span>
                <select
                  value={form.holder}
                  disabled={!activity}
                  onChange={(event) => setForm({ ...form, holder: event.target.value })}
                  required
                >
                  <option value="">{activity ? 'Choose a person' : 'Choose an activity first'}</option>
                  {byRole(activity?.holders || []).map(([role, people]) => (
                    <optgroup key={role} label={role}>
                      {people.map((person) => (
                        <option key={person.id} value={person.id}>
                          {person.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>{activity?.scope_label || 'Limited to'}</span>
                <select
                  value={form.scope}
                  disabled={!activity?.scope_options.length}
                  onChange={(event) => setForm({ ...form, scope: event.target.value })}
                >
                  <option value="">{activity ? activity.scope_all : 'Choose an activity first'}</option>
                  {(activity?.scope_options || []).map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-field acc-until">
                <span>Until</span>
                <input
                  type="date"
                  min={today}
                  value={form.ends_on}
                  disabled={form.no_end_date}
                  required={!form.no_end_date}
                  onChange={(event) => setForm({ ...form, ends_on: event.target.value })}
                  aria-label="End date"
                />
                <label className="acc-check">
                  <input
                    type="checkbox"
                    checked={form.no_end_date}
                    onChange={(event) => setForm({ ...form, no_end_date: event.target.checked, ends_on: '' })}
                  />
                  No end date
                </label>
              </div>
              <label className="form-field acc-wide">
                <span>Note (optional)</span>
                <input
                  value={form.note}
                  maxLength={255}
                  onChange={(event) => setForm({ ...form, note: event.target.value })}
                  placeholder="What should they help with?"
                />
              </label>
            </div>
            {activity ? <p className="acc-hint">{activity.description}</p> : null}
            <div className="acc-actions">
              <button className="btn" type="submit" disabled={!canGrant || Boolean(busy)}>
                {busy === 'grant' ? 'Tagging…' : 'Tag person'}
              </button>
            </div>
          </form>

          {tags.length === 0 ? (
            <p className="card studio-panel studio-empty">No one is tagged yet.</p>
          ) : (
            <section className="card studio-panel studio-table-wrap">
              <table className="studio-table">
                <thead>
                  <tr>
                    <th>Person</th>
                    <th>Activity</th>
                    <th>Limited to</th>
                    <th>Until</th>
                    <th>State</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {tags.map((tag) => (
                    <tr key={tag.id}>
                      <td>
                        {tag.holder.name}
                        <p className="studio-table-sub">
                          {tag.holder.role_label}
                          {tag.pending ? ` · ${tag.pending} waiting` : ''}
                        </p>
                      </td>
                      <td>{tag.activity_label}</td>
                      <td>{tag.scope_text}</td>
                      <td>{shortDate(tag.ends_on)}</td>
                      <td>
                        <span className={`studio-chip ${tag.state === 'active' ? 'is-approved' : 'is-wait'}`}>
                          {STATE_LABEL[tag.state]}
                        </span>
                        {tag.close_reason ? <p className="studio-table-sub">{tag.close_reason}</p> : null}
                      </td>
                      <td>
                        {tag.state === 'closed' ? null : (
                          <button
                            className="btn btn-secondary"
                            type="button"
                            disabled={Boolean(busy)}
                            onClick={() => closeTag(tag)}
                          >
                            Close
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </>
      ) : null}

      {tab === 'history' ? (
        history.length === 0 ? (
          <p className="card studio-panel studio-empty">Decided requests will appear here.</p>
        ) : (
          <section className="card studio-panel studio-table-wrap">
            <table className="studio-table">
              <thead>
                <tr>
                  <th>Request</th>
                  <th>From</th>
                  <th>Status</th>
                  <th>Decided</th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => (
                  <tr key={row.id}>
                    <td className="acc-wrap">
                      {row.summary}
                      <p className="studio-table-sub">{row.activity_label}</p>
                      <RequestChanges changes={row.changes} />
                    </td>
                    <td>
                      {row.requested_by?.name || '—'}
                      {row.requested_by ? <p className="studio-table-sub">{row.requested_by.role_label}</p> : null}
                    </td>
                    <td>
                      <span className={`studio-chip ${STATUS_CLASS[row.status] || ''}`}>{row.status_label}</span>
                      {row.decision_note || row.result?.error ? (
                        <p className="studio-table-sub">{row.result?.error || row.decision_note}</p>
                      ) : null}
                    </td>
                    <td>
                      {when(row.decided_at) || '—'}
                      {row.decided_by ? <p className="studio-table-sub">by {row.decided_by.name}</p> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )
      ) : null}
    </div>
  );
}
