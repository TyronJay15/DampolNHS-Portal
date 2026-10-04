import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowIcon, CapIcon } from '../../components/icons/SchoolIcons';
import Loading from '../../components/Loading/Loading';
import { fetchPrograms } from '../../services/publicService';
import ProgramDialog from './ProgramDialog';
import PublicLayout from './PublicLayout';
import './ProgramsPage.css';

function ProgramCard({ program, onOpen }) {
  return (
    <li className="card program-card">
      <button type="button" className="program-card-hit" onClick={onOpen} aria-haspopup="dialog">
        <span className="program-card-top">
          <CapIcon />
          {program.track ? <span className="program-track">{program.track}</span> : null}
        </span>
        <span className="program-code">{program.code}</span>
        {program.name && program.name !== program.code ? <span className="program-name">{program.name}</span> : null}
        {program.summary ? <p className="program-summary">{program.summary}</p> : null}
        <span className="program-more">
          View details <ArrowIcon />
        </span>
      </button>
    </li>
  );
}

function ProgramGroup({ title, items, onOpen }) {
  if (!items.length) return null;
  return (
    <section className="program-section">
      <h2>{title}</h2>
      <ul className="program-grid" aria-label={title}>
        {items.map((program) => (
          <ProgramCard key={program.id} program={program} onOpen={() => onOpen(program.code)} />
        ))}
      </ul>
    </section>
  );
}

export default function ProgramsPage() {
  const [programs, setPrograms] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  // The open program lives in the address (?program=STEM), so a shared link opens its details.
  const [params, setParams] = useSearchParams();
  const openCode = (params.get('program') || '').toUpperCase();
  const openProgram = programs.find((item) => item.code === openCode);

  useEffect(() => {
    fetchPrograms()
      .then((data) => setPrograms(Array.isArray(data) ? data : data.results || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  function show(code) {
    setParams(code ? { program: code } : {}, { replace: true });
  }

  const grade12 = programs.filter((item) => item.grade_level === 'Grade 12');
  const grade11 = programs.filter((item) => item.grade_level === 'Grade 11');

  return (
    <PublicLayout>
      <div className="programs public-page public-section lp-container">
        <header className="public-hero">
          <h1>Senior High School Programs</h1>
          <p>Open a strand or cluster to see its subjects and pathways, then apply — the form keeps your choice.</p>
        </header>
        {loading ? <Loading /> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <ProgramGroup title="Grade 12 Strands" items={grade12} onOpen={show} />
        <ProgramGroup title="Grade 11 Cluster Programs" items={grade11} onOpen={show} />
        <aside className="public-cta">
          <h2>Ready to start your journey?</h2>
          <p>Apply now for School Year 2025-2026</p>
          <div className="public-cta-actions">
            <Link className="btn" to="/register">
              Register Now
            </Link>
            <Link className="btn btn-secondary" to="/contact">
              Contact Us
            </Link>
          </div>
        </aside>
      </div>
      {openProgram ? <ProgramDialog program={openProgram} onClose={() => show('')} /> : null}
    </PublicLayout>
  );
}
