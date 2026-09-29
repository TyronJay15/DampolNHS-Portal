import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { cardStatusClass, cardStatusIcon, cardStatusLabel } from '../../utils/gradeStatus';
import {
  fetchAdvisory,
  fetchTeacherAssignments,
  fetchTerms,
  hideAdvisoryGrades,
  showAdvisoryGrades,
  showReadyCards,
} from '../../services/teacherService';

export default function TeacherAdvisoryPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [confirmShow, setConfirmShow] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const assignments = await fetchTeacherAssignments();
        const assignment = assignments.find((row) => String(row.id) === String(assignmentId));
        if (!assignment || !assignment.can_advise) {
          throw new Error('You are not the adviser for that section.');
        }
        const termRows = await fetchTerms(assignment.school_year_id);
        const current = termRows.find((row) => row.is_current) || termRows[0];
        if (cancelled) return;
        setTerms(termRows);
        setTermId(current ? String(current.id) : '');
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, [assignmentId]);

  useEffect(() => {
    if (!termId) return undefined;
    let cancelled = false;
    setError('');
    fetchAdvisory(assignmentId, termId)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [assignmentId, termId]);

  async function reload() {
    const payload = await fetchAdvisory(assignmentId, termId);
    setData(payload);
    return payload;
  }

  async function showReady(force = false) {
    const incomplete = (data?.students || []).filter((row) => row.can_show && !row.complete);
    if (!force && incomplete.length) {
      setConfirmShow({ bulk: true, count: incomplete.length });
      return;
    }
    setBusy('show-ready');
    setMessage('');
    setError('');
    setConfirmShow(null);
    try {
      const result = await showReadyCards(Number(assignmentId), Number(termId));
      await reload();
      setMessage(`Showed ${result.shown} card(s). ${result.skipped} had nothing new to show.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function run(action, row, force = false) {
    if (action === 'show' && !force && row.assigned && row.posted < row.assigned && !row.update_ready) {
      setConfirmShow(row);
      return;
    }
    setBusy(`${action}-${row.student_id}`);
    setMessage('');
    setError('');
    setConfirmShow(null);
    try {
      const result =
        action === 'show'
          ? await showAdvisoryGrades(Number(assignmentId), Number(termId), row.student_id)
          : await hideAdvisoryGrades(Number(assignmentId), Number(termId), row.student_id);
      await reload();
      setMessage(
        action === 'show' ? `Showed ${row.name}'s card (${result.shown}).` : `Locked ${row.name}'s card (${result.hidden}).`,
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  const students = useMemo(() => {
    const rows = data?.students || [];
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((row) =>
      [row.name, row.lrn, row.guardian_name, row.contact_number].join(' ').toLowerCase().includes(needle),
    );
  }, [data, query]);

  if (loading) return <Loading label="Loading advisory…" />;

  return (
    <div className="desk studio">
      <PageHead
        kicker={data?.section?.program || data?.section?.grade_level || 'Advisory'}
        title={data?.assignment?.section ? `${data.assignment.section} advisory` : 'Advisory section'}
        icon="advisory"
      >
        <p>
          {data
            ? `${data.roster_count} student(s). You can show a partial card; missing subjects stay off the student view until they are approved and re-shown.`
            : 'Show or lock student cards for this section.'}
        </p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
        </div>
      </PageHead>
      <div className="studio-actions">
        <Link to="/teacher/advisory">Back to advisory</Link>
        <Link to={`/teacher/advisory/${assignmentId}/records`}>Records</Link>
      </div>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-tabs">
        {terms.map((term) => (
          <button
            key={term.id}
            type="button"
            className={String(term.id) === termId ? 'is-active' : ''}
            onClick={() => setTermId(String(term.id))}
          >
            {term.label}
          </button>
        ))}
      </div>

      <section className="card studio-panel">
        <h2>
          <LineMark name="classes" />
          Subjects
        </h2>
        {!data?.subjects?.length ? (
          <p className="studio-empty">No subject teachers are assigned to this section yet.</p>
        ) : (
          <div className="studio-table-wrap">
            <table className="studio-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Teacher</th>
                  <th>Missing</th>
                  <th>Draft</th>
                  <th>Submitted</th>
                  <th>Approved</th>
                  <th>Shown</th>
                </tr>
              </thead>
              <tbody>
                {data.subjects.map((row) => (
                  <tr key={row.subject_id}>
                    <td>
                      <span className="desk-line">
                        <LineMark name="classes" size={14} />
                        {row.subject}
                      </span>
                    </td>
                    <td>{row.teacher}</td>
                    <td>{row.missing}</td>
                    <td>{row.draft}</td>
                    <td>{row.submitted}</td>
                    <td>{row.approved}</td>
                    <td>{row.released}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <label className="studio-search">
        <span className="desk-line">
          <LineMark name="search" size={14} />
          Search
        </span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, LRN, or guardian" />
      </label>

      <section className="card studio-panel">
        <h2>
          <LineMark name="user" />
          Students
        </h2>
        <div className="studio-actions">
          <button className="btn" type="button" disabled={Boolean(busy)} onClick={showReady}>
            {busy === 'show-ready' ? 'Showing…' : 'Show all ready cards'}
          </button>
        </div>
        {!data?.students?.length ? (
          <p className="studio-empty">No students are placed in this section yet.</p>
        ) : students.length === 0 ? (
          <p className="studio-empty">No students match that search.</p>
        ) : (
          <div className="studio-table-wrap">
            <table className="studio-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>LRN</th>
                  <th>Contact</th>
                  <th>Guardian</th>
                  <th>Card</th>
                  <th>Recommendation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((row) => (
                  <tr key={row.student_id}>
                    <td>
                      <span className="desk-line">
                        <LineMark name="user" size={14} />
                        {row.name}
                      </span>
                    </td>
                    <td>{row.lrn}</td>
                    <td>{row.contact_number || '—'}</td>
                    <td>
                      {row.guardian_name || '—'}
                      {row.guardian_contact ? ` · ${row.guardian_contact}` : ''}
                    </td>
                    <td>
                      <span className={`studio-status ${cardStatusClass(row)}`}>
                        <LineMark name={cardStatusIcon(row)} size={14} />
                        {cardStatusLabel(row)}
                      </span>
                    </td>
                    <td>{row.recommendation?.courses?.[0]?.name || '—'}</td>
                    <td>
                      <div className="studio-actions">
                        <button
                          className="btn"
                          type="button"
                          disabled={!row.can_show || Boolean(busy)}
                          onClick={() => run('show', row)}
                        >
                          {busy === `show-${row.student_id}` ? 'Showing…' : row.update_ready ? 'Re-show' : 'Show'}
                        </button>
                        <button
                          className="btn btn-secondary"
                          type="button"
                          disabled={!row.can_hide || Boolean(busy)}
                          onClick={() => run('hide', row)}
                        >
                          {busy === `hide-${row.student_id}` ? 'Locking…' : 'Lock'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {confirmShow?.bulk ? (
        <div className="studio-modal-backdrop">
          <div className="card studio-panel studio-modal">
            <h2>Show incomplete cards?</h2>
            <p>
              {confirmShow.count} student{confirmShow.count === 1 ? ' has' : 's have'} approved scores while other
              subjects are still missing. They will see a partial card until those subjects are approved and re-shown.
            </p>
            <div className="studio-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setConfirmShow(null)}>
                Cancel
              </button>
              <button className="btn" type="button" onClick={() => showReady(true)}>
                Show ready cards
              </button>
            </div>
          </div>
        </div>
      ) : confirmShow ? (
        <div className="studio-modal-backdrop">
          <div className="card studio-panel studio-modal">
            <h2>Show a partial card?</h2>
            <p>
              Show {confirmShow.posted} of {confirmShow.assigned} subjects for <strong>{confirmShow.name}</strong>? The
              student will see a partial card. Missing subjects stay as not yet posted.
            </p>
            <div className="studio-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setConfirmShow(null)}>
                Cancel
              </button>
              <button className="btn" type="button" onClick={() => run('show', confirmShow, true)}>
                Show partial card
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
