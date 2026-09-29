import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import DashboardShell from '../../components/Sidebar/DashboardShell';
import { fetchNotifications } from '../../services/studentService';
import '../admin/AdminChrome.css';
import '../../styles/studio.css';

export default function HeadLayout() {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    fetchNotifications()
      .then((data) => setUnread(data.unread || 0))
      .catch(() => setUnread(0));
  }, []);

  return (
    <DashboardShell
      title="Head Teacher"
      initials="HT"
      accountTo="/head/password"
      notificationTo="/head/notifications"
      notificationCount={unread}
      links={[
        { to: '/head', label: 'Overview', icon: 'home', end: true },
        { to: '/head/year', label: 'School year', icon: 'year' },
        { to: '/head/sections', label: 'Section management', icon: 'sections' },
        { to: '/head/approve', label: 'Approve grades', icon: 'approve' },
        { to: '/head/corrections', label: 'Corrections', icon: 'corrections' },
        { to: '/head/archive', label: 'Archive', icon: 'archive' },
        { to: '/head/notifications', label: 'Notifications', icon: 'bell', badge: unread || null },
        { to: '/head/events', label: 'Events', icon: 'year' },
      ]}
    >
      <div className="admin-chrome">
        <Outlet />
      </div>
    </DashboardShell>
  );
}
