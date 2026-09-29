import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
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

function matches(row, query, keys) {
  if (!query) return true;
  return keys.map((key) => row[key]).join(' ').toLowerCase().includes(query);
}

export default function TeacherRecordsPage() {
  const { user } = useAuth();
  const { encode, advise, error, loading } = useTeacherDuties();
  const [query, setQuery] = useState('');
  const [openPrograms, setOpenPrograms] = useState({});
  const [openSections, setOpenSections] = useState({});
  const [openAdvisory, setOpenAdvisory] = useState({});
  const [openedOnce, setOpenedOnce] = useState(false);

  const classPrograms = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = encode.filter((row) =>
      matches(row, needle, ['subject', 'section', 'program_code', 'grade_level']),
    );
    return groupByProgramSection(filtered);
  }, [encode, query]);

  const advisoryPrograms = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = advise.filter((row) => matches(row, needle, ['section', 'program_code', 'grade_level']));
    return groupByProgramSection(filtered);
  }, [advise, query]);

  useEffect(() => {
    if (openedOnce || (classPrograms.length === 0 && advisoryPrograms.length === 0)) return;
    const classOpen = openAllGroups(classPrograms, 'class-');
    const advisoryOpen = openAllGroups(advisoryPrograms);
    setOpenPrograms(classOpen.programsOpen);
    setOpenSections(classOpen.sectionsOpen);
    setOpenAdvisory(advisoryOpen.programsOpen);
    setOpenedOnce(true);
  }, [advisoryPrograms, classPrograms, openedOnce]);

  function toggleProgram(code, setter) {
    setter((current) => ({ ...current, [code]: !current[code] }));
  }

  function toggleSection(key, setter) {
    setter((current) => ({ ...current, [key]: !current[key] }));
  }

  if (loading) return <Loading label="Loading records…" />;

  return (
    <div className="desk studio studio-spaced">
      <PageHead kicker="History" title="Records" icon="history">
        <p>Class encode history and advisory card records, grouped by program and section.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          <span className="studio-chip">{encode.length} classes</span>
          <span className="studio-chip">{advise.length} advisory</span>
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

      <section className="card studio-panel">
        <h2>
          <LineMark name="classes" />
          Classes
        </h2>
        {classPrograms.length === 0 ? (
          <p className="studio-empty">No class records match that search.</p>
        ) : (
          <div className="studio-accordion-list">
            {classPrograms.map((program) => {
              const programOpen = Boolean(openPrograms[program.code]);
              return (
                <article className={`studio-nested-accordion${programOpen ? ' is-open' : ''}`} key={program.code}>
                  <button type="button" className="studio-accordion-head" onClick={() => toggleProgram(program.code, setOpenPrograms)}>
                    <div>
                      <p className="studio-kicker">Program</p>
                      <h3>{program.code}</h3>
                    </div>
                    <span className="studio-accordion-caret">{programOpen ? '▾' : '▸'}</span>
                  </button>
                  {programOpen ? (
                    <div className="studio-accordion-body">
                      {program.sections.map((section) => {
                        const sectionKey = `class-${program.code}-${section.name}`;
                        const sectionOpen = Boolean(openSections[sectionKey]);
                        return (
                          <article className={`studio-nested-accordion${sectionOpen ? ' is-open' : ''}`} key={sectionKey}>
                            <button type="button" className="studio-accordion-head" onClick={() => toggleSection(sectionKey, setOpenSections)}>
                              <div>
                                <p className="studio-kicker">{section.grade_level}</p>
                                <h4>{section.name}</h4>
                              </div>
                              <span className="studio-accordion-caret">{sectionOpen ? '▾' : '▸'}</span>
                            </button>
                            {sectionOpen ? (
                              <div className="studio-accordion-body">
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
                                        <Link className="btn" to={`/teacher/classes/${row.id}/records`}>
                                          Open records
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
      </section>

      <section className="card studio-panel">
        <h2>
          <LineMark name="advisory" />
          Advisory
        </h2>
        {advisoryPrograms.length === 0 ? (
          <p className="studio-empty">No advisory records match that search.</p>
        ) : (
          <div className="studio-accordion-list">
            {advisoryPrograms.map((program) => {
              const programOpen = Boolean(openAdvisory[program.code]);
              return (
                <article className={`studio-nested-accordion${programOpen ? ' is-open' : ''}`} key={`adv-${program.code}`}>
                  <button type="button" className="studio-accordion-head" onClick={() => toggleProgram(program.code, setOpenAdvisory)}>
                    <div>
                      <p className="studio-kicker">Program</p>
                      <h3>{program.code}</h3>
                    </div>
                    <span className="studio-accordion-caret">{programOpen ? '▾' : '▸'}</span>
                  </button>
                  {programOpen ? (
                    <div className="studio-accordion-body">
                      <div className="studio-task-list">
                        {program.sections.map((section) => (
                          <article className="studio-task-card" key={`adv-${program.code}-${section.name}`}>
                            <div className="studio-task-copy">
                              <h3>
                                <LineMark name="advisory" size={14} />
                                {section.name}
                              </h3>
                              <p>
                                {section.grade_level} · {section.school_year}
                              </p>
                            </div>
                            <div className="studio-actions">
                              {section.tasks.map((row) => (
                                <Link className="btn" key={row.id} to={`/teacher/advisory/${row.id}/records`}>
                                  Open records
                                </Link>
                              ))}
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
        )}
      </section>
    </div>
  );
}
