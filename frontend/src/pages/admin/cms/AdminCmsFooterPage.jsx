import { useEffect, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import FieldLabel from './FieldLabel';
import { fetchCms } from '../../../services/cmsService';
import { DEFAULT_CMS } from '../../../utils/cmsDefaults';
import CmsPhotoField from './CmsPhotoField';
import './AdminCms.css';
import { useCmsPublish } from './useCmsPublish';

const BRAND = [
  ['brandName', 'Brand name'],
  ['brandTagline', 'Tagline'],
  ['copyright', 'Copyright'],
];

const LINKS = [
  ['address', 'Address'],
  ['facebookUrl', 'Facebook URL'],
  ['facebookLabel', 'Facebook label'],
];

const PAGE = {
  document: 'footer',
  name: 'footer',
  saved: 'Footer saved.',
  publishBody: 'The footer shown on every public page updates as soon as you confirm.',
};

export default function AdminCmsFooterPage() {
  const { publish, proposing } = useCmsPublish(PAGE);
  const [form, setForm] = useState(null);
  // The page as loaded, so a tagged editor's proposal carries only what changed.
  const [loaded, setLoaded] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const defaults = DEFAULT_CMS.footer;

  useEffect(() => {
    fetchCms()
      .then((data) => {
        const next = { ...defaults, ...(data.footer || {}) };
        setForm(next);
        setLoaded(next);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      const done = await publish(form, loaded);
      if (done) setMessage(done);
    } catch (err) {
      setError(err.message);
    }
  }

  function partnerLogo() {
    return (form.columns || []).find((column) => column.id === 'fcol-partners')?.logos?.[0] || {};
  }

  function setPartnerImage(image) {
    setForm((current) => ({
      ...current,
      columns: (current.columns || []).map((column) => {
        if (column.id !== 'fcol-partners') return column;
        const previous = column.logos?.[0] || {};
        return {
          ...column,
          logos: image ? [{ id: 'deped-logo', alt: 'Department of Education logo', ...previous, image }] : [],
        };
      }),
    }));
  }

  if (loading) return <Loading label="Loading footer copy…" />;
  if (!form) return error ? <p className="alert alert-error">{error}</p> : null;

  return (
    <form onSubmit={handleSave}>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="cms-grid-3">
        <section className="card cms-card">
          <h2 className="desk-line">
            <LineMark name="cms" />
            School logo
          </h2>
          <CmsPhotoField
            label="Header, footer, and login"
            value={form.logo}
            fallback={defaults.logo}
            onChange={(logo) => setForm({ ...form, logo })}
          />
        </section>
        <section className="card cms-card">
          <h2 className="desk-line">
            <LineMark name="cms" />
            Login background
          </h2>
          <CmsPhotoField
            label="Sign-in photo"
            value={form.authImage}
            fallback={defaults.authImage}
            onChange={(authImage) => setForm({ ...form, authImage })}
          />
        </section>
        <section className="card cms-card">
          <h2 className="desk-line">
            <LineMark name="cms" />
            Partner logo
          </h2>
          <CmsPhotoField
            label="DepEd or partner"
            value={partnerLogo().image}
            fallback={defaults.columns.find((column) => column.id === 'fcol-partners')?.logos?.[0]?.image}
            onChange={setPartnerImage}
          />
        </section>
      </div>

      <div className="cms-grid-2">
        <section className="card cms-card">
          <h2 className="desk-line">
            <LineMark name="cms" />
            Brand
          </h2>
          {BRAND.map(([name, label]) => (
            <label className="form-field" key={name}>
              <FieldLabel>{label}</FieldLabel>
              <input value={form[name] || ''} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />
            </label>
          ))}
          <p className="admin-meta">Use {'{year}'} in copyright for the current year.</p>
        </section>
        <section className="card cms-card">
          <h2 className="desk-line">
            <LineMark name="home" />
            Address and social
          </h2>
          {LINKS.map(([name, label]) => (
            <label className="form-field" key={name}>
              <FieldLabel icon={name === 'address' ? 'home' : 'cms'}>{label}</FieldLabel>
              <input value={form[name] || ''} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />
            </label>
          ))}
        </section>
      </div>

      <div className="cms-save">
        <button className="btn" type="submit">
          {proposing ? 'Submit for approval' : 'Save footer'}
        </button>
      </div>
    </form>
  );
}
