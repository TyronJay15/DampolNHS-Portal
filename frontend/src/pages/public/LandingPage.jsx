import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PublicLayout from './PublicLayout';
import AnnouncementReader from '../../components/AnnouncementReader/AnnouncementReader';
import BulletinCarousel from '../../components/BulletinCarousel/BulletinCarousel';
import { fetchPublicBulletin } from '../../services/publicService';
import { DEFAULT_CMS } from '../../utils/cmsDefaults';
import { fileUrl } from '../../services/api';
import './LandingPage.css';

export default function LandingPage() {
  return (
    <PublicLayout>
      {(cms) => <LandingContent landing={{ ...DEFAULT_CMS.landing, ...(cms.landing || {}) }} />}
    </PublicLayout>
  );
}

function LandingContent({ landing }) {
  const slides = landing.slides || [];
  const [active, setActive] = useState(0);
  const [news, setNews] = useState([]);
  const [openNews, setOpenNews] = useState(null);
  const current = slides[active] || slides[0];

  useEffect(() => {
    if (slides.length < 2) return undefined;
    const id = window.setInterval(() => setActive((value) => (value + 1) % slides.length), 6000);
    return () => window.clearInterval(id);
  }, [slides.length]);

  useEffect(() => {
    fetchPublicBulletin()
      .then((rows) => setNews(rows.slice(0, 8)))
      .catch(() => setNews([]));
  }, []);

  if (!current) return null;

  return (
    <div className="landing-page">
      <section className="lp-hero">
        <div className="lp-hero-inner">
          <div>
            <div className="lp-hero-kicker">{current.kicker}</div>
            <h1 className="lp-hero-title">{current.title}</h1>
            <p className="lp-hero-body">{current.body}</p>
            <div className="lp-hero-actions">
              <Link className="lp-btn" to={current.ctaPrimary?.to || '/register'}>
                {current.ctaPrimary?.label || 'Register'}
              </Link>
              <Link className="lp-btn lp-btn-hero-secondary" to={current.ctaSecondary?.to || '/about'}>
                {current.ctaSecondary?.label || 'Learn more'}
              </Link>
            </div>
            <div className="lp-hero-dots">
              {slides.map((slide, index) => (
                <button
                  key={slide.id || slide.image}
                  type="button"
                  className={`lp-dot ${index === active ? 'active' : ''}`}
                  aria-label={`Go to slide ${index + 1}`}
                  onClick={() => setActive(index)}
                />
              ))}
            </div>
          </div>
          <div>
            <div className="lp-slide-frame">
              {current.image ? <img src={fileUrl(current.image)} alt={current.title} className="lp-slide-image" /> : <div className="lp-slide-image" />}
              <div className="lp-slide-caption">
                <div>{current.kicker}</div>
                <small>{current.title}</small>
              </div>
              <button type="button" className="lp-slide-arrow left" onClick={() => setActive((v) => (v - 1 + slides.length) % slides.length)} aria-label="Previous slide">
                ‹
              </button>
              <button type="button" className="lp-slide-arrow right" onClick={() => setActive((v) => (v + 1) % slides.length)} aria-label="Next slide">
                ›
              </button>
            </div>
            <div className="lp-slide-thumbs">
              {slides.slice(0, 4).map((slide, index) => (
                <button
                  key={slide.id || slide.image}
                  type="button"
                  className={`lp-thumb ${index === active ? 'active' : ''}`}
                  onClick={() => setActive(index)}
                >
                  {slide.image ? <img src={fileUrl(slide.image)} alt="" /> : null}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="lp-section">
        <div className="lp-container">
          <div className="lp-section-head">
            <div>
              <h2>{landing.aboutSection?.title}</h2>
              <p>{landing.aboutSection?.subtitle}</p>
            </div>
          </div>
          <div className="lp-card-grid">
            {(landing.aboutCards || []).map((card) => (
              <Link key={card.id} to={card.linkTo || '/about'} className="lp-about-card">
                <div>
                  <h3>{card.title}</h3>
                  <p>{card.body}</p>
                  <span>{card.cta}</span>
                </div>
                {card.image ? <img src={fileUrl(card.image)} alt="" /> : null}
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section lp-bulletin">
        <div className="lp-container">
          <div className="lp-section-head invert">
            <div>
              <h2>{landing.bulletinSection?.title}</h2>
              <p>{landing.bulletinSection?.subtitle}</p>
            </div>
            <Link className="lp-pill" to="/announcements">
              View news
            </Link>
          </div>
          {news.length ? (
            <BulletinCarousel items={news} onOpen={setOpenNews} />
          ) : (
            <p className="lp-bulletin-empty">No announcements or upcoming events yet. Published posts appear here.</p>
          )}
        </div>
      </section>
      <AnnouncementReader item={openNews} onClose={() => setOpenNews(null)} />

      <section className="info-banner">
        <div className="banner-container">
          {landing.banner?.logo ? <img src={fileUrl(landing.banner.logo)} alt="" className="banner-logo" /> : null}
          <div>
            <h2>{landing.banner?.schoolTitle}</h2>
            <p className="admission-text">{landing.banner?.admissionText}</p>
            <p>{landing.banner?.description}</p>
            <div className="lp-hero-actions">
              <Link className="lp-btn" to="/register">
                Enroll Now
              </Link>
              <Link className="lp-btn lp-btn-secondary" to="/login">
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
