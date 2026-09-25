import { useEffect, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import FieldLabel from './FieldLabel';
import { fetchCms, saveCmsDocument } from '../../../services/cmsService';
import { DEFAULT_CMS } from '../../../utils/cmsDefaults';
import CmsPhotoField from './CmsPhotoField';
import './AdminCms.css';

const JUMPS = [
  ['cms-hero', 'Hero slides'],
  ['cms-about', 'About cards'],
  ['cms-banner', 'Banner'],
];

function patchList(list, index, field, value) {
  return (list || []).map((item, i) => (i === index ? { ...item, [field]: value } : item));
}

function jumpTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export default function AdminCmsLandingPage() {
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const defaults = DEFAULT_CMS.landing;

  useEffect(() => {
    fetchCms()
      .then((data) => {
        const next = { ...defaults, ...(data.landing || {}) };
        next.banner = { ...defaults.banner, ...(next.banner || {}) };
        setForm(next);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setError('');
    try {
      await saveCmsDocument('landing', form);
      setMessage('Landing copy saved.');
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading label="Loading landing copy…" />;
  if (!form) return error ? <p className="alert alert-error">{error}</p> : null;

  const banner = { ...defaults.banner, ...(form.banner || {}) };

  return (
    <div className="cms-studio">
      <aside className="cms-jump">
        {JUMPS.map(([id, label]) => (
          <button key={id} type="button" onClick={() => jumpTo(id)}>
            {label}
          </button>
        ))}
      </aside>

      <form onSubmit={handleSave}>
        {message ? <p className="alert alert-info">{message}</p> : null}
        {error ? <p className="alert alert-error">{error}</p> : null}

        <section className="cms-panel" id="cms-hero">
          <div className="cms-slide-grid">
            {(form.slides || []).map((slide, index) => (
              <article className="card cms-card" key={slide.id || index}>
                <h2 className="desk-line">
                  <LineMark name="cms" />
                  Slide {index + 1}
                </h2>
                <CmsPhotoField
                  label="Photo"
                  value={slide.image}
                  fallback={defaults.slides[index]?.image}
                  onChange={(image) =>
                    setForm((current) => ({ ...current, slides: patchList(current.slides, index, 'image', image) }))
                  }
                />
                <label className="form-field">
                  <FieldLabel>Kicker</FieldLabel>
                  <input
                    value={slide.kicker || ''}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, slides: patchList(current.slides, index, 'kicker', event.target.value) }))
                    }
                  />
                </label>
                <label className="form-field">
                  <FieldLabel>Title</FieldLabel>
                  <input
                    value={slide.title || ''}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, slides: patchList(current.slides, index, 'title', event.target.value) }))
                    }
                  />
                </label>
                <label className="form-field">
                  <FieldLabel>Body</FieldLabel>
                  <textarea
                    rows={3}
                    value={slide.body || ''}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, slides: patchList(current.slides, index, 'body', event.target.value) }))
                    }
                  />
                </label>
              </article>
            ))}
          </div>
        </section>

        <section className="cms-panel" id="cms-about">
          <h2 className="desk-line">
            <LineMark name="cms" />
            About cards
          </h2>
          <div className="cms-grid-3">
            {(form.aboutCards || []).map((card, index) => (
              <article className="card cms-card" key={card.id || index}>
                <h3 className="desk-line">
                  <LineMark name="cms" size={14} />
                  {card.title || `Card ${index + 1}`}
                </h3>
                <CmsPhotoField
                  label="Photo"
                  value={card.image}
                  fallback={defaults.aboutCards[index]?.image}
                  onChange={(image) =>
                    setForm((current) => ({
                      ...current,
                      aboutCards: patchList(current.aboutCards, index, 'image', image),
                    }))
                  }
                />
              </article>
            ))}
          </div>
        </section>

        <section className="card cms-card cms-panel" id="cms-banner">
          <h2 className="desk-line">
            <LineMark name="cms" />
            Bottom banner
          </h2>
          <CmsPhotoField
            label="Banner logo"
            value={banner.logo}
            fallback={defaults.banner.logo}
            onChange={(logo) => setForm((current) => ({ ...current, banner: { ...banner, ...(current.banner || {}), logo } }))}
          />
        </section>

        <div className="cms-save">
          <button className="btn" type="submit">
            Save landing
          </button>
        </div>
      </form>
    </div>
  );
}
