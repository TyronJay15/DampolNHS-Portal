import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
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
import DutyTermTabs from './DutyTermTabs';
import { defaultTermId, dutyTerms } from './dutyTerms';
import { genderLabel } from '../../utils/gender';

export default function TeacherAdvisoryPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const confirm = useConfirm();
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  // Show and Lock apply to the open term, or to every scheduled term at once.
  const [scope, setScope] = useState('term');

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const assignments = await fetchTeacherAssignments();
        const assignment = assignments.find((row) => String(row.id) === String(assignmentId));
        if (!assignment || !assignment.can_advise) {
          throw new Error('You are not the adviser for that section.');
        }
        const termRows = dutyTerms(await fetchTerms(assignment.school_year_id), assignment);
        if (cancelled) return;
        setTerms(termRows);
        setTermId(defaultTermId(termRows));
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

  const termLabel = terms.find((term) => String(term.id) === termId)?.label || 'this term';
  const allTerms = scope === 'all';
  const target = allTerms ? 'all' : Number(termId);
  const scopeText = allTerms ? `all terms (${terms.map((term) => term.label).join(', ')})` : termLabel;

  async function showReady() {
    const ready = (data?.students || []).filter((row) => row.can_show);
    const incomplete = ready.filter((row) => !row.complete);
    const answer = await confirm({
      title: `Show ready report cards for ${allTerms ? 'all terms' : termLabel}?`,
      body: allTerms
        ? `Every student's approved subjects are shown in ${scopeText}.`
        : 'Each student will see the subjects that have been approved so far.',
      confirmLabel: allTerms ? 'Show all terms' : `Show ${ready.length}`,
      facts: allTerms ? undefined : [{ label: 'Cards to show', value: ready.length }],
      warning:
        !allTerms && incomplete.length
          ? `${incomplete.length} student${incomplete.length === 1 ? ' has' : 's have'} approved scores while other subjects are still missing. They will see a partial card until those subjects are approved and re-shown.`
          : undefined,
    });
    if (!answer) return;
    setBusy('show-ready');
    setMessage('');
    setError('');
    try {
      const result = await showReadyCards(Number(assignmentId), target);
      await reload();
      setMessage(`Showed ${result.shown} card(s) for ${result.terms.join(', ')}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function run(action, row) {
    const partial = row.assigned && row.posted < row.assigned && !row.update_ready;
    const answer =
      action === 'show'
        ? await confirm({
            title: `${row.update_ready && !allTerms ? 'Re-show' : 'Show'} ${row.name}'s report card?`,
            body: `The student will be able to see the approved subjects for ${scopeText}.`,
            confirmLabel: allTerms ? 'Show all terms' : row.update_ready ? 'Re-show card' : 'Show card',
            warning:
              partial && !allTerms
                ? `Only ${row.posted} of ${row.assigned} subjects are posted. The student will see a partial card; missing subjects stay as not yet posted.`
                : undefined,
          })
        : await confirm({
            title: `Lock ${row.name}'s report card?`,
            body: `The student will not see ${scopeText} until you show it again.`,
            confirmLabel: allTerms ? 'Lock all terms' : 'Lock card',
            tone: 'warning',
          });
    if (!answer) return;
    setBusy(`${action}-${row.student_id}`);
    setMessage('');
    setError('');
    try {
      const result =
        action === 'show'
          ? await showAdvisoryGrades(Number(assignmentId), target, row.student_id)
          : await hideAdvisoryGrades(Number(assignmentId), target, row.student_id);
      await reload();
      setMessage(
        `${action === 'show' ? 'Showed' : 'Locked'} ${row.name}'s card for ${result.terms.join(', ')}.`,
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
        <Link to={`/teacher/advisory/${assignmentId}/guidance`}>College recommendation</Link>
      </div>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <DutyTermTabs
        terms={terms}
        termId={termId}
        onChange={setTermId}
        empty="No subject of this section is scheduled in any term yet. The Head Teacher sets it in the term plan."
      />

      {terms.length ? (
        <>
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
              <div className="studio-tabs" role="radiogroup" aria-label="Show and lock apply to">
                <button type="button" role="radio" aria-checked={!allTerms} className={allTerms ? '' : 'is-active'} onClick={() => setScope('term')}>
                  {termLabel}
                </button>
                <button type="button" role="radio" aria-checked={allTerms} className={allTerms ? 'is-active' : ''} onClick={() => setScope('all')}>
                  All terms
                </button>
              </div>
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
                          {row.gender ? <p className="studio-table-sub">{genderLabel(row.gender)}</p> : null}
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
                              disabled={!(allTerms || row.can_show) || Boolean(busy)}
                              onClick={() => run('show', row)}
                            >
                              {busy === `show-${row.student_id}` ? 'Showing…' : row.update_ready && !allTerms ? 'Re-show' : 'Show'}
                            </button>
                            <button
                              className="btn btn-secondary"
                              type="button"
                              disabled={!(allTerms || row.can_hide) || Boolean(busy)}
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
        </>
      ) : null}
    </div>
  );
}
