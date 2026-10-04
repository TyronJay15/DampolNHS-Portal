import { useEffect, useMemo, useState } from 'react';
import { useProposal } from '../../components/Access/proposalContext';
import { useConfirm } from '../../components/ConfirmDialog/useConfirm';
import LineMark from '../../components/LineMark/LineMark';
import { fetchTermPlan, saveTermPlan } from '../../services/adminService';
import './TermPlanPanel.css';

const TERMS = [1, 2, 3];
const SET_ALL = [
  { value: '1,2,3', label: 'All terms' },
  { value: '1', label: 'Term 1 only' },
  { value: '2', label: 'Term 2 only' },
  { value: '3', label: 'Term 3 only' },
];

function keyOf(program, subjectId) {
  return `${program.id}:${subjectId}`;
}

function sameTerms(a, b) {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`;
}

// Which terms each program subject runs in, for one school year at a time.
// Edits (one by one, or with the bulk tools) stay local until saved together.
export default function TermPlanPanel({ years }) {
  const confirm = useConfirm();
  // Set when a teacher tagged to prepare the term plan opens it: saving becomes a request.
  const proposal = useProposal();
  const [yearId, setYearId] = useState(() => {
    const current = years.find((row) => row.is_current) || years[0];
    return current ? current.id : null;
  });
  const [plan, setPlan] = useState(null);
  const [programId, setProgramId] = useState(null);
  const [draft, setDraft] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!yearId) return undefined;
    let live = true;
    fetchTermPlan(yearId)
      .then((data) => {
        if (!live) return;
        setPlan(data);
        setProgramId((current) => (data.programs.some((item) => item.id === current) ? current : data.programs[0]?.id ?? null));
        setDraft({});
      })
      .catch((err) => live && setError(err.message));
    return () => {
      live = false;
    };
  }, [yearId]);

  const rows = useMemo(
    () => (plan ? plan.programs.flatMap((program) => program.subjects.map((row) => ({ ...row, program }))) : []),
    [plan],
  );

  if (!yearId) return <p className="card studio-panel studio-empty">Open a school year first.</p>;
  if (!plan) return error ? <p className="alert alert-error">{error}</p> : null;

  const year = plan.school_year;
  const editable = year.editable;
  const termsOf = (program, subject) => draft[keyOf(program, subject.subject_id)] || subject.terms;
  const changes = rows.filter((row) => !sameTerms(termsOf(row.program, row), row.terms));
  const changedPrograms = new Set(changes.map((row) => row.program.id));
  const program = plan.programs.find((item) => item.id === programId);
  const sources = plan.programs.filter((item) => item.id !== programId && item.subjects.length);

  function setTerms(entries) {
    setDraft((items) => ({ ...items, ...Object.fromEntries(entries) }));
  }

  function toggle(subject, number) {
    const current = termsOf(program, subject);
    const next = current.includes(number) ? current.filter((value) => value !== number) : [...current, number].sort();
    if (next.length) setTerms([[keyOf(program, subject.subject_id), next]]);
  }

  function setEverySubject(value) {
    const terms = value.split(',').map(Number);
    setTerms(program.subjects.map((subject) => [keyOf(program, subject.subject_id), terms]));
    setMessage(`Every ${program.code} subject set to ${SET_ALL.find((item) => item.value === value).label}. Review, then save.`);
  }

  // Shared subjects (for example the core subjects) take the other program's terms; the rest stay as they are.
  function copyFrom(sourceId) {
    const source = plan.programs.find((item) => item.id === Number(sourceId));
    const theirs = new Map(source.subjects.map((subject) => [subject.subject_id, termsOf(source, subject)]));
    const shared = program.subjects.filter((subject) => theirs.has(subject.subject_id));
    setTerms(shared.map((subject) => [keyOf(program, subject.subject_id), theirs.get(subject.subject_id)]));
    setMessage(
      shared.length
        ? `Copied ${plural(shared.length, 'shared subject')} from ${source.code}. Review, then save.`
        : `${source.code} has no subjects in common with ${program.code}.`,
    );
  }

  async function changeYear(nextId) {
    if (changes.length) {
      const answer = await confirm({
        title: 'Discard unsaved changes?',
        body: `${plural(changes.length, 'subject')} in the ${year.label} plan ${changes.length === 1 ? 'is' : 'are'} not saved yet.`,
        confirmLabel: 'Discard and switch',
        tone: 'warning',
      });
      if (!answer) return;
    }
    setMessage('');
    setError('');
    setPlan(null);
    setYearId(Number(nextId));
  }

  async function proposeChanges() {
    setError('');
    setMessage('');
    try {
      const sent = await proposal.propose(
        {
          school_year: year.id,
          rows: changes.map((row) => ({ program: row.program.id, subject: row.subject_id, terms: termsOf(row.program, row) })),
        },
        {
          title: `Propose the ${year.label} term plan changes?`,
          facts: [
            { label: 'Subjects changed', value: changes.length },
            { label: 'Programs', value: changedPrograms.size },
          ],
        },
      );
      if (!sent) return;
      setDraft({});
      setMessage('Sent to the Head Teacher for approval. Follow it under My access.');
    } catch (err) {
      setError(err.message);
    }
  }

  async function save() {
    if (proposal) return proposeChanges();
    const leftOut = changes.filter((row) => row.graded_terms.some((number) => !termsOf(row.program, row).includes(number)));
    const answer = await confirm({
      title: `Save the ${year.label} term plan?`,
      body: 'Teachers encode, and students see, each subject only in the terms you ticked.',
      confirmLabel: 'Save term plan',
      tone: leftOut.length ? 'warning' : 'standard',
      facts: [
        { label: 'Subjects changed', value: changes.length },
        { label: 'Programs', value: changedPrograms.size },
      ],
      warning: leftOut.length
        ? `${plural(leftOut.length, 'subject')} already ${leftOut.length === 1 ? 'has' : 'have'} grades in a term you removed. Those grades stay visible, but no new grades can be encoded there.`
        : undefined,
    });
    if (!answer) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const saved = await saveTermPlan(
        year.id,
        changes.map((row) => ({ program: row.program.id, subject: row.subject_id, terms: termsOf(row.program, row) })),
      );
      setPlan(saved);
      setDraft({});
      const kept = saved.outside ? ` ${plural(saved.outside, 'existing grade')} outside the new plan were kept.` : '';
      setMessage(`Saved ${plural(saved.saved, 'subject')}.${kept}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card studio-panel tplan">
      <header className="tplan-head">
        <div>
          <h2>
            <LineMark name="year" />
            Term plan
          </h2>
          <p>Tick the terms each subject runs in. Teachers encode it, and students see it, only in those terms.</p>
        </div>
        <label className="tplan-year">
          <span>School year</span>
          <select value={yearId} disabled={busy} onChange={(event) => changeYear(event.target.value)}>
            {years.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
                {row.is_current ? ' (current)' : ''}
              </option>
            ))}
          </select>
        </label>
      </header>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}
      {editable ? null : <p className="alert alert-info">This year is archived, so its term plan is read-only.</p>}

      {plan.programs.length === 0 ? (
        <p className="studio-empty">No programs at your grade levels for this year.</p>
      ) : (
        <>
          <div className="tplan-programs" role="tablist" aria-label="Programs">
            {plan.programs.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={item.id === programId}
                className={`tplan-program${item.id === programId ? ' is-active' : ''}`}
                onClick={() => setProgramId(item.id)}
              >
                {item.code}
                <small>{item.grade_level.replace('Grade ', 'G')}</small>
                {changedPrograms.has(item.id) ? <i aria-label="unsaved changes" /> : null}
              </button>
            ))}
          </div>

          {program && editable && program.subjects.length ? (
            <div className="tplan-tools">
              <label>
                <span>Set every subject to</span>
                <select value="" disabled={busy} onChange={(event) => setEverySubject(event.target.value)}>
                  <option value="">Choose…</option>
                  {SET_ALL.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              {sources.length ? (
                <label>
                  <span>Copy plan from</span>
                  <select value="" disabled={busy} onChange={(event) => copyFrom(event.target.value)}>
                    <option value="">Choose a program…</option>
                    {sources.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.code} · {item.grade_level}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>
          ) : null}

          {program ? (
            <div className="studio-table-wrap">
              <table className="studio-table tplan-table">
                <caption>{program.name}</caption>
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th className="tplan-kind">Type</th>
                    {TERMS.map((number) => (
                      <th key={number} className="tplan-term">
                        <span className="tplan-long">Term {number}</span>
                        <span className="tplan-short" aria-hidden="true">
                          T{number}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {program.subjects.length === 0 ? (
                    <tr>
                      <td colSpan={2 + TERMS.length}>No subjects on this program yet. The Admin adds them in Programs.</td>
                    </tr>
                  ) : null}
                  {program.subjects.map((subject) => {
                    const terms = termsOf(program, subject);
                    return (
                      <tr key={subject.subject_id} className={sameTerms(terms, subject.terms) ? '' : 'is-changed'}>
                        <td className="tplan-subject">{subject.name}</td>
                        <td className="tplan-kind">{subject.kind}</td>
                        {TERMS.map((number) => {
                          const on = terms.includes(number);
                          const graded = subject.graded_terms.includes(number);
                          return (
                            <td key={number} className="tplan-term">
                              <label
                                className={`tplan-check${on ? ' is-on' : ''}${graded && !on ? ' is-orphan' : ''}`}
                                title={graded ? 'Grades already exist in this term' : undefined}
                              >
                                <input
                                  type="checkbox"
                                  checked={on}
                                  disabled={!editable || busy || (on && terms.length === 1)}
                                  onChange={() => toggle(subject, number)}
                                  aria-label={`${subject.name} runs in Term ${number}`}
                                />
                                <span aria-hidden="true">{on ? '✓' : ''}</span>
                                {graded ? <em aria-hidden="true" /> : null}
                              </label>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}

          <footer className="tplan-foot">
            <p className="tplan-legend">
              <em aria-hidden="true" /> has grades · every subject keeps at least one term
            </p>
            {editable && changes.length ? (
              <div className="tplan-actions">
                <span>{plural(changes.length, 'unsaved change')}</span>
                <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => setDraft({})}>
                  Discard
                </button>
                <button className="btn" type="button" disabled={busy} onClick={save}>
                  {busy ? 'Saving…' : proposal ? 'Submit for approval' : 'Save term plan'}
                </button>
              </div>
            ) : null}
          </footer>
        </>
      )}
    </section>
  );
}
