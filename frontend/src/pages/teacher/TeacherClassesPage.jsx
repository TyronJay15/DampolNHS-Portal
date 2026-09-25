import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { useTeacherDuties } from './useTeacherDuties';

export default function TeacherClassesPage() {
  const { user } = useAuth();
  const { encode, error, loading } = useTeacherDuties();
  const [query, setQuery] = useState('');

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return encode;
    return encode.filter((row) =>
      [row.subject, row.section, row.program_code, row.grade_level].join(' ').toLowerCase().includes(needle),
    );
  }, [encode, query]);

  if (loading) return <Loading label="Loading classes…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Encode" title="Classes" icon="classes">
        <p>Open a section table, pick Term 1–3, encode, then submit for Head Teacher approval.</p>
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
      {rows.length === 0 ? (
        <p className="card studio-panel studio-empty">No subject-teacher sections match that search.</p>
      ) : (
        <div className="studio-cards">
          {rows.map((row) => (
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
      )}
    </div>
  );
}
