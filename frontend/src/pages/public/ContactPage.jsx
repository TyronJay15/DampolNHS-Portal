import PublicLayout from './PublicLayout';
import { ClockIcon, FacebookIcon, MailIcon, PhoneIcon, PinIcon } from '../../components/icons/SchoolIcons';
import './ContactPage.css';

function safeUrl(value, fallback) {
  try {
    const url = new URL(String(value || '').trim());
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : fallback;
  } catch {
    return fallback;
  }
}

const ICONS = {
  Address: PinIcon,
  Phone: PhoneIcon,
  Email: MailIcon,
  'Office hours': ClockIcon,
};

export default function ContactPage() {
  return (
    <PublicLayout>
      {(cms) => {
        const contact = cms.contact || {};
        const deped = safeUrl(contact.deped_url, 'https://www.deped.gov.ph/');
        const facebook = safeUrl(contact.facebook_url, 'https://www.facebook.com/D1stNHS/');
        const items = [
          ['Address', contact.address],
          ['Phone', contact.phone],
          ['Email', contact.email],
          ['Office hours', contact.hours],
        ].filter(([, value]) => value);
        return (
          <div className="contact public-page public-section lp-container">
            <header className="public-hero">
              <h1>{contact.title || 'Contact Us'}</h1>
              <p className="public-hero-kicker">{contact.subtitle}</p>
              <p>{contact.description}</p>
            </header>
            <article className="card contact-panel">
              <h2>General Information</h2>
              <ul className="contact-list">
                {items.map(([label, value]) => {
                  const Icon = ICONS[label];
                  return (
                    <li key={label}>
                      {Icon ? <Icon /> : null}
                      <div>
                        <h3>{label}</h3>
                        <p>{value}</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </article>
            <section className="card contact-follow">
              <h2>Follow Us</h2>
              <p>School announcements and updates are posted on our Facebook page.</p>
              <div className="contact-follow-links">
                <a className="contact-facebook" href={facebook} target="_blank" rel="noreferrer">
                  <FacebookIcon />
                  Dampol 1st NHS on Facebook
                </a>
                <a className="contact-deped" href={deped} target="_blank" rel="noreferrer">
                  Official DepEd website
                </a>
              </div>
            </section>
          </div>
        );
      }}
    </PublicLayout>
  );
}
