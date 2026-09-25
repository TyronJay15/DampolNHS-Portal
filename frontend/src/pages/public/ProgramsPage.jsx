import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowIcon, CapIcon } from '../../components/icons/SchoolIcons';
import Loading from '../../components/Loading/Loading';
import { fetchPrograms } from '../../services/publicService';
import PublicLayout from './PublicLayout';
import './ProgramsPage.css';

function subjectLabel(subject) {
  return typeof subject === 'string' ? subject : subject.name;
}

function subjectKey(subject, index) {
  if (typeof subject === 'string') return subject;
  return subject.code || subject.name || String(index);
}

function ProgramCard({ program, isOpen, onOpen, onClose }) {
  const subjects = program.subjects || [];
  const pathways = program.pathways || [];
  return (
    <li
      className={`card program-card${isOpen ? ' is-open' : ''}`}
      onMouseEnter={onOpen}
      onMouseLeave={onClose}
      onFocus={onOpen}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) onClose();
      }}
    >
      <button
        type="button"
        className="program-card-hit"
        aria-expanded={isOpen}
        aria-controls={`program-info-${program.code}`}
        onClick={() => {
          if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
          if (isOpen) onClose();
          else onOpen();
        }}
      >
        <span className="program-card-top">
          <CapIcon />
          {program.track ? <span className="program-track">{program.track}</span> : null}
        </span>
        <span className="program-code">{program.code}</span>
        {program.name && program.name !== program.code ? <span className="program-name">{program.name}</span> : null}
        {program.summary ? <p className="program-summary">{program.summary}</p> : null}
        <span className="program-more">
          Learn more <ArrowIcon />
        </span>
      </button>
      <div className="program-popout" id={`program-info-${program.code}`}>
        {program.description ? <p>{program.description}</p> : null}
        {subjects.length ? (
          <div>
            <h3>Program subjects</h3>
            <ul>
              {subjects.map((subject, index) => (
                <li key={subjectKey(subject, index)}>{subjectLabel(subject)}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {pathways.length ? (
          <div>
            <h3>Possible pathways</h3>
            <ul>
              {pathways.map((pathway) => (
                <li key={pathway}>{pathway}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <Link className="btn" to={`/register?program=${encodeURIComponent(program.code)}`}>
          Register Now
        </Link>
      </div>
    </li>
  );
}

function ProgramGroup({ title, items, openCode, setOpenCode }) {
  if (!items.length) return null;
  return (
    <section className="program-section">
      <h2>{title}</h2>
      <ul className="program-grid" aria-label={title}>
        {items.map((program) => (
          <ProgramCard
            key={program.id}
            program={program}
            isOpen={openCode === program.code}
            onOpen={() => setOpenCode(program.code)}
            onClose={() => setOpenCode('')}
          />
        ))}
      </ul>
    </section>
  );
}

export default function ProgramsPage() {
  const [programs, setPrograms] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [openCode, setOpenCode] = useState('');

  useEffect(() => {
    fetchPrograms()
      .then((data) => setPrograms(Array.isArray(data) ? data : data.results || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const grade12 = programs.filter((item) => item.grade_level === 'Grade 12');
  const grade11 = programs.filter((item) => item.grade_level === 'Grade 11');

  return (
    <PublicLayout>
      <div className="programs public-page public-section lp-container">
        <header className="public-hero">
          <h1>Senior High School Programs</h1>
          <p>Hover or tap a strand or cluster to see what it covers. Register when you are ready — the form keeps your selection.</p>
        </header>
        {loading ? <Loading /> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}
        <ProgramGroup title="Grade 12 Strands" items={grade12} openCode={openCode} setOpenCode={setOpenCode} />
        <ProgramGroup title="Grade 11 Cluster Programs" items={grade11} openCode={openCode} setOpenCode={setOpenCode} />
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
    </PublicLayout>
  );
}
