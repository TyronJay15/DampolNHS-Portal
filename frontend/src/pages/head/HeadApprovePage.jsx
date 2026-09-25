import { useEffect, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { approveGrades, fetchGradeQueues, fetchSchoolYears, returnGrades } from '../../services/adminService';
import { fetchTerms } from '../../services/teacherService';

export default function HeadApprovePage() {
  const { user } = useAuth();
  const [terms, setTerms] = useState([]);
  const [termId, setTermId] = useState('');
  const [groups, setGroups] = useState([]);
  const [busyKey, setBusyKey] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSchoolYears()
      .then((years) => {
        const current = years.find((year) => year.is_current) || years[0];
        if (!current) return [];
        return fetchTerms(current.id);
      })
      .then((termRows) => {
        setTerms(termRows);
        const current = termRows.find((row) => row.is_current) || termRows[0];
        setTermId(current ? String(current.id) : '');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!termId) return undefined;
    let cancelled = false;
    fetchGradeQueues(termId)
      .then((data) => {
        if (!cancelled) setGroups(data.groups || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [termId]);

  async function runAction(group, action) {
    const key = `${action}-${group.section_id}-${group.subject_id}`;
    setBusyKey(key);
    setMessage('');
    setError('');
    try {
      const payload = { term: Number(termId), section: group.section_id, subject: group.subject_id };
      const result = action === 'approve' ? await approveGrades(payload) : await returnGrades(payload);
      const data = await fetchGradeQueues(termId);
      setGroups(data.groups || []);
      if (action === 'approve') {
        setMessage(`Approved ${result.approved} grade(s).`);
      } else {
        setMessage(
          `Returned ${result.returned} hidden grade(s) to draft.` +
            (result.still_shown ? ` ${result.still_shown} shown card(s) left untouched.` : ''),
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey('');
    }
  }

  if (loading) return <Loading label="Loading submitted classes…" />;

  const waiting = groups.filter((row) => row.submitted > 0).length;

  return (
    <div className="desk studio">
      <PageHead kicker="Review" title="Approve grades" icon="approve">
        <p>Approve submitted section tables. Advisers can show a card only after every assigned subject is approved.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          <span className="studio-chip">{waiting} waiting</span>
          <span className="studio-chip">{groups.length} classes</span>
        </div>
      </PageHead>
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

      {groups.length === 0 ? <p className="card studio-panel studio-empty">No encoded grades for this term yet.</p> : null}
      <div className="studio-cards">
        {groups.map((group) => (
          <article className="card studio-card" key={`${group.section_id}-${group.subject_id}`}>
            <p className="studio-kicker">{group.section}</p>
            <h2>
              <DeskMark name="approve" size={16} />
              {group.subject}
            </h2>
            <p className="studio-empty">
              Draft {group.draft} · Submitted {group.submitted} · Approved {group.approved} · Shown {group.released}
            </p>
            <div className="studio-actions">
              <button
                className="btn"
                type="button"
                disabled={!group.submitted || busyKey.startsWith('approve')}
                onClick={() => runAction(group, 'approve')}
              >
                {busyKey === `approve-${group.section_id}-${group.subject_id}` ? 'Approving…' : 'Approve submitted'}
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                disabled={(!group.submitted && !group.approved) || group.released || busyKey.startsWith('return')}
                onClick={() => runAction(group, 'return')}
              >
                {busyKey === `return-${group.section_id}-${group.subject_id}` ? 'Returning…' : 'Return to draft'}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
