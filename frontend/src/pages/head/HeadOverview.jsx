import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Loading from '../../components/Loading/Loading';
import DeskMark from '../../components/DeskMark/DeskMark';
import WelcomeBanner from '../../components/WelcomeBanner/WelcomeBanner';
import UpcomingEvents from '../../components/UpcomingEvents/UpcomingEvents';
import PublicLinks from '../../components/PublicLinks/PublicLinks';
import { fetchAssignments, fetchPlacements, fetchSchoolYears, fetchSections } from '../../services/adminService';

const SHORTCUTS = [
  { to: '/head/year', label: 'School year', icon: 'year' },
  { to: '/head/sections', label: 'Sections', icon: 'sections' },
  { to: '/head/place', label: 'Place students', icon: 'place' },
  { to: '/head/assign', label: 'Assign teachers', icon: 'assign' },
  { to: '/head/approve', label: 'Approve grades', icon: 'approve' },
  { to: '/head/corrections', label: 'Corrections', icon: 'corrections' },
  { to: '/head/archive', label: 'Archive', icon: 'archive' },
];

export default function HeadOverview() {
  const [year, setYear] = useState(null);
  const [sections, setSections] = useState(0);
  const [unplaced, setUnplaced] = useState(0);
  const [assignments, setAssignments] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchSchoolYears(), fetchSections(), fetchPlacements(), fetchAssignments()])
      .then(([years, sectionRows, placementRows, assignmentRows]) => {
        setYear(years.find((row) => row.is_current) || years[0] || null);
        setSections(sectionRows.length);
        setUnplaced(placementRows.filter((row) => !row.placed).length);
        setAssignments(assignmentRows.length);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading head teacher desk…" />;

  return (
    <div className="desk studio">
      <WelcomeBanner>
        <p className="dash-hero-kicker">School operations</p>
        <h1>Head Teacher</h1>
        <p>Open the year, build sections, place students, assign teachers, then approve grades. Advisers show or lock cards.</p>
        <div className="studio-hero-meta">
          <span className="studio-chip">{year?.label || 'No school year'}</span>
          <span className="studio-chip">{year?.is_current ? 'Current year' : 'Set a current year'}</span>
        </div>
      </WelcomeBanner>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="desk-stats">
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="sections" size={16} />
            Sections
          </span>
          <strong>{sections}</strong>
        </article>
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="place" size={16} />
            Unplaced students
          </span>
          <strong>{unplaced}</strong>
        </article>
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="assign" size={16} />
            Teacher duties
          </span>
          <strong>{assignments}</strong>
        </article>
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="year" size={16} />
            School year
          </span>
          <strong>{year?.label || '—'}</strong>
        </article>
      </div>

      <section>
        <div className="desk-section-head">
          <h2>Quick access</h2>
        </div>
        <nav className="desk-quick-row">
          {SHORTCUTS.map((item) => (
            <Link to={item.to} key={item.to}>
              <DeskMark name={item.icon} />
              {item.label}
            </Link>
          ))}
        </nav>
      </section>

      <div className="desk-extras">
        <UpcomingEvents to="/head/events" />
        <PublicLinks />
      </div>
    </div>
  );
}
