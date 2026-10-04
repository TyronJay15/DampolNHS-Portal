import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useConfirm } from '../ConfirmDialog/useConfirm';
import { beginSignOut, finishSignOut, isSigningOut } from '../PostLoginLoader/signOutStore';
import { useCms } from '../../hooks/useCms';
import { useTheme } from '../../hooks/useTheme';
import { fileUrl } from '../../services/api';
import Icon from '../Icon/Icon';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import './DashboardShell.css';
import '../../styles/desk.css';

export default function DashboardShell({
  title,
  subtitle = 'Dampol 1st National High School',
  initials,
  links,
  accountTo,
  notificationTo,
  notificationCount = 0,
  children,
}) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const cms = useCms();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const [open, setOpen] = useState(false);
  const logo = cms?.footer?.logo || '';
  const brand = initials || title.slice(0, 2).toUpperCase();

  async function signOut() {
    if (isSigningOut()) return;
    const answer = await confirm({
      title: 'Log out?',
      body: 'You will need to sign in again to continue.',
      confirmLabel: 'Log out',
      cancelLabel: 'Stay signed in',
      icon: 'logout',
    });
    if (!answer || isSigningOut()) return;
    // The overlay goes up first, and signing out starts at the same moment. Tokens and the signed-in user are
    // cleared as soon as it settles; the overlay only fades out afterwards, over the login page.
    beginSignOut();
    let confirmed = false;
    try {
      confirmed = await logout();
    } finally {
      finishSignOut({ offline: !confirmed });
    }
    navigate('/login', { replace: true });
  }

  return (
    <div className={`dash${open ? ' is-side-open' : ''}`} data-theme={theme}>
      <button
        type="button"
        className={`dash-overlay${open ? ' is-on' : ''}`}
        aria-label="Close menu"
        onClick={() => setOpen(false)}
      />
      <aside className="dash-side" aria-hidden={!open} inert={!open}>
        <div className="dash-brand">
          {logo ? (
            <img src={fileUrl(logo)} alt="" className="dash-logo-img" />
          ) : (
            <div className="dash-logo">{brand}</div>
          )}
          <div>
            <strong>{title}</strong>
            <small>{subtitle}</small>
            <em className="dash-motto">Thy Light Shall Guide Us!</em>
          </div>
        </div>
        <nav>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} onClick={() => setOpen(false)}>
              {link.icon ? (
                <span className="dash-nav-well">
                  <Icon name={link.icon} size={16} />
                </span>
              ) : null}
              <span>{link.label}</span>
              {link.badge ? <span className="dash-badge">{link.badge}</span> : null}
            </NavLink>
          ))}
        </nav>
        <div className="dash-foot">
          {accountTo ? (
            <NavLink to={accountTo} className="dash-account" onClick={() => setOpen(false)}>
              <span className="dash-nav-well">
                <Icon name="account" size={16} />
              </span>
              <span>My Account</span>
            </NavLink>
          ) : null}
          <button type="button" className="dash-logout" onClick={signOut}>
            Logout
          </button>
        </div>
      </aside>
      <div className="dash-body">
        <header className="dash-top">
          <button
            type="button"
            className="dash-menu"
            aria-label={open ? 'Hide menu' : 'Show menu'}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            ☰
          </button>
          <div className="dash-top-copy">
            <strong>{title}</strong>
            <small>{subtitle}</small>
          </div>
          <div className="dash-top-tools">
            {notificationTo ? (
              <Link className="dash-bell" to={notificationTo} aria-label="Notifications">
                <Icon name="bell" size={18} />
                {notificationCount ? <span className="dash-badge is-top">{notificationCount}</span> : null}
              </Link>
            ) : null}
            <ThemeToggle theme={theme} onToggle={toggle} />
            <div className="dash-userchip">
              <span>{brand}</span>
              <em>
                {user?.first_name} {user?.last_name}
              </em>
            </div>
          </div>
        </header>
        <main className="dash-main">{children}</main>
      </div>
    </div>
  );
}
