import { Link } from 'react-router-dom';
import { formatFooterText, isExternalUrl } from '../../utils/cmsDefaults';
import { fileUrl } from '../../services/api';
import './Footer.css';

function FooterLink({ link }) {
  const label = String(link?.label || '').trim();
  const href = String(link?.to || '').trim();
  if (!label || !href) return null;
  if (isExternalUrl(href)) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="lp-footer-link">
        {label}
      </a>
    );
  }
  return (
    <Link to={href} className="lp-footer-link">
      {label}
    </Link>
  );
}

export default function Footer({ content }) {
  const footer = content || {};
  const columns = footer.columns || [];
  const facebook = footer.facebookUrl;

  return (
    <footer className="lp-footer">
      <div className="lp-container">
        <div className="lp-footer-grid" style={{ '--lp-footer-cols': Math.max(columns.length, 1) }}>
          <div>
            <div className="lp-footer-logoRow">
              {footer.logo ? <img src={fileUrl(footer.logo)} alt="" className="lp-footer-logo" /> : null}
              <div>
                <div className="lp-footer-name">{footer.brandName || 'Dampol 1st National High School'}</div>
                <div className="lp-footer-sub">{footer.brandTagline || 'Grade Portal'}</div>
              </div>
            </div>
            <div className="lp-footer-address">
              {footer.address || 'Dampol, Pulilan, Bulacan, Philippines'}
              {footer.addressNote ? (
                <>
                  <br />
                  <span className="lp-footer-muted">{footer.addressNote}</span>
                </>
              ) : null}
            </div>
            {facebook ? (
              <a href={facebook} target="_blank" rel="noopener noreferrer" className="lp-footer-link">
                {footer.facebookLabel || 'Facebook Page'}
              </a>
            ) : null}
          </div>

          {columns.map((column) => (
            <div key={column.id || column.title}>
              <div className="lp-footer-colTitle">{column.title}</div>
              {(column.links || []).map((link) => (
                <FooterLink key={link.id || link.label} link={link} />
              ))}
              {(column.logos || []).length ? (
                <div className="lp-footer-partnerRow">
                  {(column.logos || []).map((logo) =>
                    logo.image ? (
                      <img key={logo.id || logo.image} src={fileUrl(logo.image)} alt={logo.alt || ''} className="lp-partnerLogo" />
                    ) : null,
                  )}
                </div>
              ) : null}
            </div>
          ))}
        </div>

        <div className="lp-footer-bottom">
          <div className="lp-footer-muted">{formatFooterText(footer.copyright || '© {year} Dampol 1st National High School')}</div>
          <div className="lp-footer-bottomLinks">
            {(footer.bottomLinks || []).map((link) => (
              <FooterLink key={link.id || link.label} link={link} />
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
