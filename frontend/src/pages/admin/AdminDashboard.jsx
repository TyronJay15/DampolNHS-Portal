import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ForecastBars from '../../components/ForecastCharts/ForecastBars';
import DeskMark from '../../components/DeskMark/DeskMark';
import Icon from '../../components/Icon/Icon';
import YearChip from '../../components/YearChip';
import { fetchGrade11Forecast, fetchRegistrations, fetchStaffAccounts } from '../../services/adminService';
import { useAuth } from '../../context/AuthContext';
import WelcomeBanner from '../../components/WelcomeBanner/WelcomeBanner';
import UpcomingEvents from '../../components/UpcomingEvents/UpcomingEvents';
import PublicLinks from '../../components/PublicLinks/PublicLinks';
import { forecastStats } from '../../utils/forecastStats';
import './AdminHome.css';

const ACTIONS = [
  { to: '/admin/accounts', label: 'Review students', icon: 'user' },
  { to: '/admin/accounts/staff', label: 'Teacher accounts', icon: 'staff' },
  { to: '/admin/forecast', label: 'Full forecast', icon: 'forecast' },
  { to: '/admin/audit', label: 'Audit log', icon: 'audit' },
  { to: '/admin/history', label: 'Grade history', icon: 'history' },
  { to: '/admin/cms', label: 'Website CMS', icon: 'cms' },
];

export default function AdminDashboard() {
  const { user } = useAuth();
  const [counts, setCounts] = useState({ pending: '…', students: '…', teachers: '…', headTeachers: '…', admins: '…' });
  const [pendingRows, setPendingRows] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      fetchRegistrations('pending'),
      fetchStaffAccounts(),
      fetchGrade11Forecast().catch(() => null),
    ])
      .then(([regs, staff, forecastData]) => {
        const rows = Array.isArray(staff) ? staff : [];
        setCounts({
          pending: regs.counts?.pending ?? 0,
          students: regs.counts?.approved ?? 0,
          teachers: rows.filter((row) => row.role === 'teacher').length,
          headTeachers: rows.filter((row) => row.role === 'head_teacher').length,
          admins: rows.filter((row) => row.role === 'admin').length,
        });
        setPendingRows((regs.results || []).slice(0, 5));
        setForecast(forecastData);
      })
      .catch((err) => setError(err.message));
  }, []);

  const stats = forecastStats(forecast);
  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div className="desk admin-home">
      <WelcomeBanner>
        <p className="dash-hero-kicker">{today}</p>
        <h1>Welcome back{user?.first_name ? `, ${user.first_name}` : ''}</h1>
        <p>Live counts from registrations, staff logins, and approved Grade 11 students.</p>
        <div className="studio-hero-meta">
          <YearChip user={user} />
        </div>
      </WelcomeBanner>
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="desk-stats admin-desk-stats">
        <Link className="desk-stat is-pending" to="/admin/accounts">
          <span className="desk-stat-top">
            <DeskMark name="user" size={16} />
            Pending students
          </span>
          <strong>{counts.pending}</strong>
        </Link>
        <Link className="desk-stat is-ok" to="/admin/accounts">
          <span className="desk-stat-top">
            <DeskMark name="grades" size={16} />
            Approved students
          </span>
          <strong>{counts.students}</strong>
        </Link>
        <Link className="desk-stat" to="/admin/accounts/staff">
          <span className="desk-stat-top">
            <DeskMark name="staff" size={16} />
            Teachers
          </span>
          <strong>{counts.teachers}</strong>
        </Link>
        <Link className="desk-stat" to="/admin/accounts/staff">
          <span className="desk-stat-top">
            <DeskMark name="approve" size={16} />
            Head teacher
          </span>
          <strong>{counts.headTeachers}</strong>
        </Link>
        <Link className="desk-stat" to="/admin/accounts/staff">
          <span className="desk-stat-top">
            <DeskMark name="account" size={16} />
            Administrators
          </span>
          <strong>{counts.admins}</strong>
        </Link>
      </div>

      <div className="desk-extras">
        <UpcomingEvents to="/admin/events" />
        <PublicLinks />
      </div>

      <div className="desk-split">
        <div className="desk-main">
          <section className="card desk-tile">
            <div className="admin-tile-head">
              <h2 className="desk-title">
                <DeskMark name="user" size={16} />
                Pending review
              </h2>
              <Link to="/admin/accounts">Open list</Link>
            </div>
            {pendingRows.length ? (
              <ul className="admin-queue">
                {pendingRows.map((row) => (
                  <li key={row.id}>
                    <strong>
                      {row.first_name} {row.last_name}
                    </strong>
                    <span>
                      {row.program_code} · {row.grade_level_enrollment}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="desk-empty">No students are waiting for approval.</p>
            )}
          </section>

          <section className="card desk-tile">
            <div className="admin-tile-head">
              <h2 className="desk-title">
                <DeskMark name="forecast" size={16} />
                Grade 11 forecast
              </h2>
              <Link to="/admin/forecast">Full charts</Link>
            </div>
            <p className={stats.total ? 'admin-forecast-lead' : 'desk-empty'}>
              {stats.total
                ? `${stats.total} approved Grade 11 student${stats.total === 1 ? '' : 's'} ${stats.total === 1 ? 'maps' : 'map'} to ${stats.nextYear || 'next year'}.`
                : 'No approved Grade 11 registrations yet.'}
            </p>
            <ForecastBars
              rows={stats.appliedClusters}
              total={stats.appliedTotal}
              empty="Cluster counts appear after Grade 11 applications."
            />
          </section>

          <section className="card desk-tile">
            <h2>Quick actions</h2>
            <div className="admin-action-grid">
              {ACTIONS.map((item) => (
                <Link key={item.to} className="admin-action" to={item.to}>
                  <Icon name={item.icon} size={16} />
                  {item.label}
                </Link>
              ))}
            </div>
          </section>
        </div>

        <aside className="desk-rail">
          <section className="card desk-tile">
            <h2 className="desk-title">
              <DeskMark name="staff" size={16} />
              Staff mix
            </h2>
            <dl className="admin-mix">
              <div>
                <dt>Teachers</dt>
                <dd>{counts.teachers}</dd>
              </div>
              <div>
                <dt>Head teacher</dt>
                <dd>{counts.headTeachers}</dd>
              </div>
              <div>
                <dt>Admins</dt>
                <dd>{counts.admins}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>
    </div>
  );
}
