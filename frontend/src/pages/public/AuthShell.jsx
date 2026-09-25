import { useEffect, useState } from 'react';
import { fetchCms } from '../../services/publicService';
import { fileUrl } from '../../services/api';
import { DEFAULT_CMS } from '../../utils/cmsDefaults';
import './AuthShell.css';

export default function AuthShell({ title, wide, className = '', children }) {
  const [logo, setLogo] = useState(DEFAULT_CMS.footer.logo);
  const [authImage, setAuthImage] = useState(DEFAULT_CMS.footer.authImage);
  const shellClass = ['auth-shell', wide ? 'is-wide' : '', className].filter(Boolean).join(' ');

  useEffect(() => {
    fetchCms()
      .then((data) => {
        const footer = { ...DEFAULT_CMS.footer, ...(data.footer || {}) };
        setLogo(footer.logo || '');
        setAuthImage(footer.authImage || '');
      })
      .catch(() => {});
  }, []);

  return (
    <div className={shellClass}>
      <div
        className="auth-bg"
        aria-hidden="true"
        style={authImage ? { backgroundImage: `radial-gradient(ellipse at center, rgba(11, 43, 90, 0.38), rgba(11, 43, 90, 0.68)), url('${fileUrl(authImage)}')` } : undefined}
      />
      <div className="auth-card">
        <header className="auth-head">
          {logo ? <img src={fileUrl(logo)} alt="Dampol 1st National High School logo" className="auth-logo" /> : null}
          <p className="auth-school">Dampol 1st National High School</p>
          <h1>{title}</h1>
          <p className="auth-motto">Thy Light Shall Guide Us!</p>
        </header>
        {children}
      </div>
    </div>
  );
}
