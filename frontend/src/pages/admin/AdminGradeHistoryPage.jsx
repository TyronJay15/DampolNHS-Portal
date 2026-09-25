import { useEffect, useMemo, useState } from 'react';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchGradeHistory, fetchGradeReport, fetchSchoolYears } from '../../services/adminService';
import { fetchTerms } from '../../services/teacherService';

function formatWhen(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function scoreCell(entry) {
  if (!entry?.score) return '—';
  return entry.score;
}

export default function AdminGradeHistoryPage() {
  const [tab, setTab] = useState('report');
  const [years, setYears] = useState([]);
  const [terms, setTerms] = useState([]);
  const [yearId, setYearId] = useState('');
  const [termId, setTermId] = useState('');
  const [query, setQuery] = useState('');
  const [report, setReport] = useState({ year: null, term: null, sections: [] });
  const [log, setLog] = useState([]);
  const [openId, setOpenId] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchSchoolYears(), fetchGradeHistory()])
      .then(([yearRows, historyRows]) => {
        setYears(yearRows);
        setLog(historyRows);
        const current = yearRows.find((row) => row.is_current) || yearRows[0];
        setYearId(current ? String(current.id) : '');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!yearId) return undefined;
    let cancelled = false;
    fetchTerms(yearId)
      .then((termRows) => {
        if (cancelled) return;
        setTerms(termRows);
        const current = termRows.find((row) => row.is_current) || termRows[0];
        setTermId(current ? String(current.id) : '');
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [yearId]);

  useEffect(() => {
    if (!yearId || !termId) return undefined;
    let cancelled = false;
    fetchGradeReport({ school_year: yearId, term: termId })
      .then((payload) => {
        if (cancelled) return;
        setReport(payload);
        setOpenId(payload.sections?.[0]?.section_id ?? null);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [yearId, termId]);

  const sections = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return report.sections || [];
    return (report.sections || [])
      .map((section) => ({
        ...section,
        students: section.students.filter((row) =>
          [row.name, row.lrn, section.name, section.program_code].join(' ').toLowerCase().includes(needle),
        ),
      }))
      .filter((section) => section.students.length > 0 || `${section.name} ${section.program_code}`.toLowerCase().includes(needle));
  }, [report.sections, query]);

  const logRows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return log;
    return log.filter((row) =>
      [row.student, row.lrn, row.subject, row.term, row.changed_by, row.reason].join(' ').toLowerCase().includes(needle),
    );
  }, [log, query]);

  if (loading) return <Loading label="Loading grade history…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Records" title="Grade history" icon="history">
        <p>Class report is the live snapshot for a year and term. The change log is the immutable score trail.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{report.year?.label || 'No year'}</span>
          <span className="studio-chip">{report.term?.label || 'No term'}</span>
        </div>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="studio-filters">
        <button type="button" className={`studio-filter${tab === 'report' ? ' is-active' : ''}`} onClick={() => setTab('report')}>
          Class report
        </button>
        <button type="button" className={`studio-filter${tab === 'log' ? ' is-active' : ''}`} onClick={() => setTab('log')}>
          Change log
        </button>
      </div>

      <div className="studio-toolbar">
        {tab === 'report' ? (
          <>
            <label className="studio-search">
              <span className="desk-line">
                <LineMark name="year" size={14} />
                School year
              </span>
              <select value={yearId} onChange={(event) => setYearId(event.target.value)}>
                {years.map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="studio-search">
              <span className="desk-line">
                <LineMark name="year" size={14} />
                Term
              </span>
              <select value={termId} onChange={(event) => setTermId(event.target.value)}>
                {terms.map((term) => (
                  <option key={term.id} value={term.id}>
                    {term.label}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : null}
        <label className="studio-search">
          <span className="desk-line">
            <LineMark name="search" size={14} />
            Search
          </span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={tab === 'report' ? 'Student, LRN, or section' : 'Student, subject, or actor'}
          />
        </label>
      </div>

      {tab === 'report' ? (
        sections.length === 0 ? (
          <p className="card studio-panel studio-empty">No class report for that year and term.</p>
        ) : (
          sections.map((section) => {
            const open = openId === section.section_id;
            return (
              <section className="card studio-panel" key={section.section_id}>
                <button
                  className="studio-expand"
                  type="button"
                  onClick={() => setOpenId(open ? null : section.section_id)}
                >
                  <div>
                    <p className="studio-kicker">
                      {section.grade_level} · {section.program_code}
                    </p>
                    <h2>
                      <DeskMark name="sections" size={16} />
                      {section.display_label || section.name}
                    </h2>
                    <p className="studio-empty">
                      {section.adviser ? `Adviser ${section.adviser}` : 'No adviser'} · {section.shown_count}/
                      {section.student_count} shown
                    </p>
                  </div>
                  <span className="studio-chip studio-chip-soft">
                    {open ? 'Hide' : 'Open'}
                  </span>
                </button>
                {open ? (
                  <div className="studio-table-wrap">
                    <table className="studio-table">
                      <thead>
                        <tr>
                          <th>Student</th>
                          <th>LRN</th>
                          {section.subjects.map((subject) => (
                            <th key={subject.id}>{subject.name}</th>
                          ))}
                          <th>Card</th>
                          <th>Recommendation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.students.map((row) => (
                          <tr key={row.student_id}>
                            <td>
                              <span className="desk-line">
                                <LineMark name="user" size={14} />
                                {row.name}
                              </span>
                            </td>
                            <td>{row.lrn}</td>
                            {section.subjects.map((subject) => (
                              <td key={subject.id}>{scoreCell(row.scores?.[String(subject.id)])}</td>
                            ))}
                            <td>
                              <span className={`studio-status ${row.shown ? 'is-shown' : ''}`}>
                                {row.shown ? 'Shown' : 'Hidden'}
                              </span>
                            </td>
                            <td>{row.recommendation?.courses?.[0]?.name || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </section>
            );
          })
        )
      ) : logRows.length === 0 ? (
        <p className="card studio-panel studio-empty">No grade changes recorded yet.</p>
      ) : (
        <div className="card studio-table-wrap">
          <table className="studio-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Student</th>
                <th>Subject</th>
                <th>Change</th>
                <th>Who</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {logRows.map((row) => (
                <tr key={row.id}>
                  <td>{formatWhen(row.changed_at)}</td>
                  <td>
                    <span className="desk-line">
                      <LineMark name="user" size={14} />
                      {row.student}
                    </span>
                    <br />
                    {row.lrn}
                  </td>
                  <td>
                    {row.subject}
                    <br />
                    {row.term}
                  </td>
                  <td>
                    {row.previous_score || '—'} → {row.new_score || '—'}
                    <br />
                    {row.from_status || 'new'} → {row.to_status}
                  </td>
                  <td>
                    {row.changed_by || '—'}
                    <br />
                    {(row.duty || '').replaceAll('_', ' ')}
                  </td>
                  <td>{row.reason || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
