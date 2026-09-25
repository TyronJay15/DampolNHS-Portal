import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { homePathForRole } from '../../services/authService';
import { fileUrl } from '../../services/api';
import './Navbar.css';

const LINKS = [
  { to: '/', label: 'HOME' },
  { to: '/programs', label: 'PROGRAMS' },
  { to: '/announcements', label: 'NEWS' },
  { to: '/contact', label: 'CONTACT' },
  { to: '/about', label: 'ABOUT' },
];

export default function Navbar({ isScrolled = false, logo = '/logo/logodampol.jpg' }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <header className={`public-navbar ${isScrolled ? 'is-scrolled' : ''} ${open ? 'is-open' : ''}`}>
      <div className="public-nav-container">
        <Link to="/" className="public-logo-link" onClick={() => setOpen(false)}>
          {logo ? (
            <img src={fileUrl(logo)} alt="Dampol 1st National High School logo" className="public-nav-logo" />
          ) : null}
          <span className="public-school-name">Dampol 1st National Highschool</span>
        </Link>

        <button
          type="button"
          className="public-nav-toggle"
          aria-expanded={open}
          aria-label={open ? 'Close menu' : 'Open menu'}
          onClick={() => setOpen((value) => !value)}
        >
          <span />
          <span />
          <span />
        </button>

        <div className="public-nav-panel">
          <nav>
            <ul className="public-nav-links">
              {LINKS.map((link) => (
                <li key={link.to}>
                  <NavLink to={link.to} end={link.to === '/'} onClick={() => setOpen(false)}>
                    {link.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="public-nav-cta">
            {user ? (
              <Link className="public-register-btn" to={homePathForRole(user.role)} onClick={() => setOpen(false)}>
                Dashboard
              </Link>
            ) : (
              <>
                <Link className="public-login-btn" to="/login" onClick={() => setOpen(false)}>
                  Login
                </Link>
                <Link className="public-register-btn" to="/register" onClick={() => setOpen(false)}>
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
      {open ? (
        <button type="button" className="public-nav-backdrop" aria-label="Close menu" onClick={() => setOpen(false)} />
      ) : null}
    </header>
  );
}
