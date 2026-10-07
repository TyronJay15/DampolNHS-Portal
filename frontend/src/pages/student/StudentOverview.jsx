import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Loading from '../../components/Loading/Loading';
import DeskMark from '../../components/DeskMark/DeskMark';
import YearChip from '../../components/YearChip';
import { useAuth } from '../../context/AuthContext';
import { fetchNotifications, fetchStudentGrades, fetchStudentMe } from '../../services/studentService';
import WelcomeBanner from '../../components/WelcomeBanner/WelcomeBanner';
import UpcomingEvents from '../../components/UpcomingEvents/UpcomingEvents';
import PublicLinks from '../../components/PublicLinks/PublicLinks';
import GuidanceSummaryCard from './guidance/GuidanceSummaryCard';
import './StudentStudio.css';

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function StudentOverview() {
  const { user } = useAuth();
  const [me, setMe] = useState(null);
  const [notes, setNotes] = useState([]);
  const [unread, setUnread] = useState(0);
  const [card, setCard] = useState({ subjects: [], grades: [], school_year: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchStudentMe(),
      fetchNotifications().catch(() => ({ notifications: [], unread: 0 })),
      fetchStudentGrades().catch(() => ({ subjects: [], grades: [], school_year: '' })),
    ])
      .then(([profile, noticeData, grades]) => {
        setMe(profile);
        setNotes((noticeData.notifications || []).slice(0, 3));
        setUnread(noticeData.unread || 0);
        setCard({
          subjects: grades.subjects || [],
          grades: grades.grades || [],
          school_year: grades.school_year || '',
        });
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading your dashboard…" />;

  const section = me?.section;
  const subjectCount = me?.subjects?.length || card.subjects.length || 0;
  const shownScores = card.grades.filter((row) => row.score != null && row.score !== '').length;
  const yearLabel = user?.current_school_year?.label || card.school_year || me?.school_year || 'School year pending';

  return (
    <div className="desk student-studio">
      <WelcomeBanner>
        <p className="dash-hero-kicker">{greeting()}</p>
        <h1>Welcome back, {me?.first_name || 'Student'}</h1>
        <p>
          {section?.display_label
            ? section.display_label
            : section
              ? `${section.program || me?.program || 'Program'} · ${section.name}`
              : 'Your section will appear here after placement.'}
        </p>
        <div className="student-hero-meta">
          <span className="student-chip">{section?.grade_level || me?.grade_level || 'Grade pending'}</span>
          {user?.current_school_year?.label ? (
            <YearChip user={user} className="student-chip" />
          ) : (
            <span className="student-chip">{yearLabel}</span>
          )}
          <span className="student-chip">{unread ? `${unread} new notices` : 'Inbox clear'}</span>
        </div>
      </WelcomeBanner>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <section>
        <div className="desk-section-head">
          <h2>Quick access</h2>
        </div>
        <nav className="desk-quick-row">
          <Link to="/student/profile">
            <DeskMark name="user" />
            My Profile
          </Link>
          <Link to="/student/grades">
            <DeskMark name="grades" />
            Grades
          </Link>
          <Link to="/student/notifications">
            <DeskMark name="bell" />
            Notifications
            {unread ? <em>{unread}</em> : null}
          </Link>
        </nav>
      </section>

      <div className="desk-extras">
        <UpcomingEvents to="/student/events" />
        <PublicLinks />
      </div>

      <div className="desk-stats">
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="sections" size={16} />
            Section
          </span>
          <strong>{section?.display_label || section?.name || '—'}</strong>
        </article>
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="advisory" size={16} />
            Adviser
          </span>
          <strong>{section?.adviser || 'Pending'}</strong>
        </article>
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="classes" size={16} />
            Subjects
          </span>
          <strong>{subjectCount || '—'}</strong>
        </article>
        <article className="desk-stat">
          <span className="desk-stat-top">
            <DeskMark name="grades" size={16} />
            Shown scores
          </span>
          <strong>{shownScores}</strong>
        </article>
      </div>

      <div className="desk-split">
        <div className="desk-main">
          <article className="card desk-tile">
            <h2>
              <span className="desk-title">
                <DeskMark name="grades" size={16} />
                Grades
              </span>
            </h2>
            <p className="desk-empty">
              {card.school_year ? `${card.school_year}. ` : ''}
              {shownScores
                ? `${shownScores} shown score${shownScores === 1 ? '' : 's'} are on your card.`
                : 'No scores are visible yet. The adviser must show your card first.'}
            </p>
            <Link className="btn btn-secondary" to="/student/grades">
              Open grades
            </Link>
          </article>

          <article className="card desk-tile">
            <h2>
              <span className="desk-title">
                <DeskMark name="bell" size={16} />
                Notices
              </span>
              {unread ? <em>{unread} new</em> : null}
            </h2>
            {notes.length ? (
              <ul className="student-home-notes">
                {notes.map((row) => (
                  <li key={row.id} className={row.is_read ? '' : 'is-unread'}>
                    <strong>{row.title}</strong>
                    <span>{row.body}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="desk-empty">No notifications yet.</p>
            )}
            <Link className="btn btn-secondary" to="/student/notifications">
              All notifications
            </Link>
          </article>

          <GuidanceSummaryCard />
        </div>

        <aside className="desk-rail">
          <article className="card desk-tile">
            <h2>
              <span className="desk-title">
                <DeskMark name="user" size={16} />
                Enrollment
              </span>
            </h2>
            <dl className="student-facts">
              <div>
                <dt>Program</dt>
                <dd>{section?.program || me?.program || '—'}</dd>
              </div>
              <div>
                <dt>Grade</dt>
                <dd>{section?.grade_level || me?.grade_level || '—'}</dd>
              </div>
              <div>
                <dt>LRN</dt>
                <dd>{me?.lrn || '—'}</dd>
              </div>
              <div>
                <dt>Contact</dt>
                <dd>{me?.contact_number || 'Add on Profile'}</dd>
              </div>
            </dl>
          </article>
        </aside>
      </div>
    </div>
  );
}
