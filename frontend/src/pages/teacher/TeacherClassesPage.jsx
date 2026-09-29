import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { groupByProgramSection, openAllGroups } from './groupTeacherDuties';
import { useTeacherDuties } from './useTeacherDuties';
import { progressChipClass } from '../../utils/gradeStatus';

function EncodeChips({ row }) {
  const current = row.progress?.current;
  if (!current) return null;
  return (
    <div className="studio-chip-row">
      <span className={`studio-chip ${progressChipClass(current.progress)}`}>{current.progress_label}</span>
      {current.workflow_label ? <span className="studio-chip is-approved">{current.workflow_label}</span> : null}
    </div>
  );
}

function SectionEncodeSummary({ tasks }) {
  const terms = tasks[0]?.progress?.terms || [];
  if (!tasks.length) return null;
  return (
    <div className="studio-table-wrap studio-summary-table">
      <table className="studio-table">
        <thead>
          <tr>
            <th>Subject</th>
            {terms.map((term) => (
              <th key={term.term_id}>{term.term}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tasks.map((row) => (
            <tr key={row.id}>
              <td>{row.subject}</td>
              {(row.progress?.terms || terms).map((term) => (
                <td key={term.term_id}>
                  {term.progress_label}
                  {term.workflow_label ? ` · ${term.workflow_label}` : ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TeacherClassesPage() {
  const { user } = useAuth();
  const { encode, error, loading } = useTeacherDuties();
  const [query, setQuery] = useState('');
  const [openPrograms, setOpenPrograms] = useState({});
  const [openSections, setOpenSections] = useState({});
  const [openedOnce, setOpenedOnce] = useState(false);

  const programs = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = needle
      ? encode.filter((row) =>
          [row.subject, row.section, row.program_code, row.grade_level].join(' ').toLowerCase().includes(needle),
        )
      : encode;
    return groupByProgramSection(filtered);
  }, [encode, query]);

  useEffect(() => {
    if (openedOnce || programs.length === 0) return;
    const { programsOpen, sectionsOpen } = openAllGroups(programs);
    setOpenPrograms(programsOpen);
    setOpenSections(sectionsOpen);
    setOpenedOnce(true);
  }, [openedOnce, programs]);

  function toggleProgram(code) {
    setOpenPrograms((current) => ({ ...current, [code]: !current[code] }));
  }

  function toggleSection(key) {
    setOpenSections((current) => ({ ...current, [key]: !current[key] }));
  }

  if (loading) return <Loading label="Loading classes…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="Encode" title="Classes" icon="classes">
        <p>Classes are grouped by program and section. Subject cards show whether encoding is finished for the current term.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          <span className="studio-chip">{encode.length} assigned</span>
        </div>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      <label className="studio-search">
        <span className="desk-line">
          <LineMark name="search" size={14} />
          Search
        </span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Subject or section" />
      </label>
      {programs.length === 0 ? (
        <p className="card studio-panel studio-empty">No subject-teacher sections match that search.</p>
      ) : (
        <div className="studio-accordion-list">
          {programs.map((program) => {
            const programOpen = Boolean(openPrograms[program.code]);
            return (
              <article className={`card studio-panel studio-accordion-card${programOpen ? ' is-open' : ''}`} key={program.code}>
                <button type="button" className="studio-accordion-head" onClick={() => toggleProgram(program.code)}>
                  <div>
                    <p className="studio-kicker">Program</p>
                    <h2>
                      <DeskMark name="sections" size={16} />
                      {program.code}
                    </h2>
                    <p className="studio-empty">{program.sections.length} section(s)</p>
                  </div>
                  <span className="studio-accordion-caret">{programOpen ? '▾' : '▸'}</span>
                </button>
                {programOpen ? (
                  <div className="studio-accordion-body">
                    {program.sections.map((section) => {
                      const sectionKey = `${program.code}-${section.name}`;
                      const sectionOpen = Boolean(openSections[sectionKey]);
                      return (
                        <article
                          className={`studio-nested-accordion${sectionOpen ? ' is-open' : ''}`}
                          key={sectionKey}
                        >
                          <button type="button" className="studio-accordion-head" onClick={() => toggleSection(sectionKey)}>
                            <div>
                              <p className="studio-kicker">{section.grade_level}</p>
                              <h3>{section.name}</h3>
                              <p className="studio-empty">{section.tasks.length} subject(s) · {section.school_year}</p>
                            </div>
                            <span className="studio-accordion-caret">{sectionOpen ? '▾' : '▸'}</span>
                          </button>
                          {sectionOpen ? (
                            <div className="studio-accordion-body">
                              <SectionEncodeSummary tasks={section.tasks} />
                              <div className="studio-task-list">
                                {section.tasks.map((row) => (
                                  <article className="studio-task-card" key={row.id}>
                                    <div className="studio-task-copy">
                                      <h3>
                                        <LineMark name="classes" size={14} />
                                        {row.subject}
                                      </h3>
                                      <p>
                                        {row.grade_level} · {row.school_year}
                                        {row.progress?.current?.term ? ` · ${row.progress.current.term}` : ''}
                                      </p>
                                      <EncodeChips row={row} />
                                    </div>
                                    <div className="studio-actions">
                                      <Link className="btn" to={`/teacher/classes/${row.id}`}>
                                        Encode
                                      </Link>
                                      <Link className="btn btn-secondary" to={`/teacher/classes/${row.id}/records`}>
                                        Records
                                      </Link>
                                    </div>
                                  </article>
                                ))}
                              </div>
                            </div>
                          ) : null}
                        </article>
                      );
                    })}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
