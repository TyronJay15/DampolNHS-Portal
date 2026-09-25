import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import DeskMark from '../../components/DeskMark/DeskMark';
import LineMark from '../../components/LineMark/LineMark';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { useTeacherDuties } from './useTeacherDuties';

export default function TeacherAdvisoryListPage() {
  const { user } = useAuth();
  const { advise, error, loading } = useTeacherDuties();
  const [query, setQuery] = useState('');

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return advise;
    return advise.filter((row) =>
      [row.section, row.program_code, row.grade_level].join(' ').toLowerCase().includes(needle),
    );
  }, [advise, query]);

  if (loading) return <Loading label="Loading advisory…" />;

  return (
    <div className="desk studio">
      <PageHead kicker="Advisory" title="Show and Lock" icon="advisory">
        <p>When every assigned subject is approved, show the card. Lock hides it from the student again.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          <span className="studio-chip">{advise.length} sections</span>
        </div>
      </PageHead>
      {error ? <p className="alert alert-error">{error}</p> : null}
      <label className="studio-search">
        <span className="desk-line">
          <LineMark name="search" size={14} />
          Search
        </span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Section or program" />
      </label>
      {rows.length === 0 ? (
        <p className="card studio-panel studio-empty">No advisory sections assigned yet.</p>
      ) : (
        <div className="studio-cards">
          {rows.map((row) => (
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
                <Link className="btn" to={`/teacher/advisory/${row.id}`}>
                  Cards
                </Link>
                <Link className="btn btn-secondary" to={`/teacher/advisory/${row.id}/records`}>
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
