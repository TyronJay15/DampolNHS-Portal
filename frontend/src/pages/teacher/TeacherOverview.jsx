import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Loading from '../../components/Loading/Loading';
import DeskMark from '../../components/DeskMark/DeskMark';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import WelcomeBanner from '../../components/WelcomeBanner/WelcomeBanner';
import DashboardAnnouncements from '../../components/DashboardAnnouncements/DashboardAnnouncements';
import UpcomingEvents from '../../components/UpcomingEvents/UpcomingEvents';
import PublicLinks from '../../components/PublicLinks/PublicLinks';
import { fetchTeacherAssignments } from '../../services/teacherService';

export default function TeacherOverview() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeacherAssignments()
      .then(setRows)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading your desk…" />;

  const encode = rows.filter((row) => row.can_encode);
  const advise = rows.filter((row) => row.can_advise);

  return (
    <div className="desk studio">
      <WelcomeBanner>
        <p className="dash-hero-kicker">Teaching desk</p>
        <h1>Welcome back{user?.first_name ? `, ${user.first_name}` : ''}</h1>
        <p>Encode the sections the Head Teacher assigned to you. Advisory is Show and Lock only.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
          <span className="studio-chip">{encode.length} encode tables</span>
          <span className="studio-chip">{advise.length} advisory</span>
        </div>
      </WelcomeBanner>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <section>
        <div className="desk-section-head">
          <h2>Quick access</h2>
        </div>
        <nav className="desk-quick-row">
          <Link to="/teacher/classes">
            <DeskMark name="classes" />
            Classes
            <em>{encode.length}</em>
          </Link>
          <Link to="/teacher/advisory">
            <DeskMark name="advisory" />
            Advisory
            <em>{advise.length}</em>
          </Link>
        </nav>
      </section>

      <div className="desk-extras">
        <div className="desk-main">
          <DashboardAnnouncements />
          <UpcomingEvents to="/teacher/events" />
        </div>
        <PublicLinks />
      </div>

      {rows.length === 0 ? (
        <p className="card desk-tile desk-empty">No active assignments yet. Ask the Head Teacher to assign a class.</p>
      ) : null}

      {encode.length ? (
        <section>
          <div className="desk-section-head">
            <h3>
              <DeskMark name="classes" size={16} />
              Encode
            </h3>
          </div>
          <div className="desk-cards">
            {encode.map((row) => (
              <Link className="desk-card" to={`/teacher/classes/${row.id}`} key={row.id}>
                <p className="desk-kicker">{row.program_code || row.grade_level}</p>
                <h2>
                  {row.subject} · {row.section}
                </h2>
                <p className="desk-empty">{row.school_year}</p>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {advise.length ? (
        <section>
          <div className="desk-section-head">
            <h3>
              <DeskMark name="advisory" size={16} />
              Advisory
            </h3>
          </div>
          <div className="desk-cards">
            {advise.map((row) => (
              <Link className="desk-card" to={`/teacher/advisory/${row.id}`} key={row.id}>
                <p className="desk-kicker">{row.program_code || row.grade_level}</p>
                <h2>{row.section}</h2>
                <p className="desk-empty">{row.school_year} · Show and Lock</p>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
