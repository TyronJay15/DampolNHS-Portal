import { Link } from 'react-router-dom';
import PublicLayout from './PublicLayout';
import {
  BookIcon,
  CapIcon,
  EyeIcon,
  HeartIcon,
  QuoteIcon,
  TargetIcon,
  TrophyIcon,
  UsersIcon,
} from '../../components/icons/SchoolIcons';
import { cmsLines, cmsPairs } from '../../utils/cmsDefaults';
import './AboutPage.css';

const TILES = [
  ['Established', 'established', CapIcon],
  ['Motto', 'motto', QuoteIcon],
  ['Vision', 'vision', EyeIcon],
  ['Mission', 'mission', TargetIcon],
];
const FEATURE_ICONS = [UsersIcon, BookIcon, HeartIcon];

export default function AboutPage() {
  return (
    <PublicLayout>
      {(cms) => {
        const about = cms.about || {};
        const history = cmsPairs(about.history);
        const achievements = cmsLines(about.achievements);
        const features = cmsPairs(about.why_choose);
        return (
          <div className="about-page public-page public-section lp-container">
            <header className="public-hero">
              <h1>{about.title || 'About Our School'}</h1>
              <p className="public-hero-kicker">Excellence in education since {about.established || '1965'}</p>
              <p>{about.subtitle || about.body}</p>
            </header>
            <div className="about-grid">
              {TILES.map(([title, key, Icon]) => (
                <article className="card lift-card about-card" key={title}>
                  <Icon />
                  <h2>{title}</h2>
                  <p>{key === 'motto' && about[key] ? `"${about[key]}"` : about[key]}</p>
                </article>
              ))}
            </div>
            {history.length ? (
              <article className="card about-block">
                <h2>Our History</h2>
                <ol className="about-timeline">
                  {history.map(([year, event]) => (
                    <li key={`${year}-${event}`}>
                      {year ? <span>{year}</span> : null}
                      <p>{event}</p>
                    </li>
                  ))}
                </ol>
              </article>
            ) : null}
            {achievements.length ? (
              <article className="card about-block">
                <h2>Our Achievements</h2>
                <ul className="about-achievements">
                  {achievements.map((text) => (
                    <li key={text}>
                      <TrophyIcon />
                      <p>{text}</p>
                    </li>
                  ))}
                </ul>
              </article>
            ) : null}
            {features.length ? (
              <article className="card about-block">
                <h2>Why Choose Dampol 1st?</h2>
                <ul className="about-features">
                  {features.map(([title, body], index) => {
                    const Icon = FEATURE_ICONS[index % FEATURE_ICONS.length];
                    return (
                      <li key={title || body}>
                        <Icon />
                        {title ? <h3>{title}</h3> : null}
                        <p>{body}</p>
                      </li>
                    );
                  })}
                </ul>
              </article>
            ) : null}
            <aside className="public-cta">
              <h2>{about.cta_title || 'Join our community'}</h2>
              <p>{about.cta_body || 'Register for the next school year, or contact the school office.'}</p>
              <div className="public-cta-actions">
                <Link className="btn" to="/register">
                  Register Now
                </Link>
                <Link className="btn btn-secondary" to="/contact">
                  Contact Us
                </Link>
              </div>
            </aside>
          </div>
        );
      }}
    </PublicLayout>
  );
}
