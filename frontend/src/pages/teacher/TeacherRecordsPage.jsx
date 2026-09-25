import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { useTeacherDuties } from './useTeacherDuties';

function matches(row, query, keys) {
  if (!query) return true;
  return keys.map((key) => row[key]).join(' ').toLowerCase().includes(query);
}

export default function TeacherRecordsPage() {
  const { user } = useAuth();
  const { encode, advise, error, loading } = useTeacherDuties();
  const [query, setQuery] = useState('');

  const classRows = useMemo(
    () => encode.filter((row) => matches(row, query.trim().toLowerCase(), ['subject', 'section', 'program_code', 'grade_level'])),
    [encode, query],
  );
  const advisoryRows = useMemo(
    () => advise.filter((row) => matches(row, query.trim().toLowerCase(), ['section', 'program_code', 'grade_level'])),
    [advise, query],
  );

  if (loading) return <Loading label="Loading records…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="History" title="Records" icon="history">
        <p>Class encode history and advisory card records, kept in two lists.</p>
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
        {classRows.length === 0 ? (
          <p className="studio-empty">No class records match that search.</p>
        ) : (
          <div className="studio-cards">
            {classRows.map((row) => (
              <article className="card studio-card" key={row.id}>
                <p className="studio-kicker">
                  {row.grade_level} · {row.program_code}
                </p>
                <h2>
                  <DeskMark name="classes" size={16} />
                  {row.subject} · {row.section}
                </h2>
                <p className="studio-empty">{row.school_year}</p>
                <div className="studio-actions">
                  <Link className="btn" to={`/teacher/classes/${row.id}/records`}>
                    Open records
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="card studio-panel">
        <h2>
          <LineMark name="advisory" />
          Advisory
        </h2>
        {advisoryRows.length === 0 ? (
          <p className="studio-empty">No advisory records match that search.</p>
        ) : (
          <div className="studio-cards">
            {advisoryRows.map((row) => (
              <article className="card studio-card" key={row.id}>
                <p className="studio-kicker">
                  {row.grade_level} · {row.program_code}
                </p>
                <h2>
                  <DeskMark name="advisory" size={16} />
                  {row.section}
                </h2>
                <p className="studio-empty">{row.school_year}</p>
                <div className="studio-actions">
                  <Link className="btn" to={`/teacher/advisory/${row.id}/records`}>
                    Open records
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
