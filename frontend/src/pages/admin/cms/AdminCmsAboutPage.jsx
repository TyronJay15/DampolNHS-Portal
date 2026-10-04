import { useEffect, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import { fetchCms } from '../../../services/cmsService';
import { DEFAULT_CMS } from '../../../utils/cmsDefaults';
import './AdminCms.css';
import { useCmsPublish } from './useCmsPublish';

const GROUPS = [
  {
    title: 'Identity',
    fields: [
      ['title', 'Title'],
      ['subtitle', 'Subtitle'],
      ['motto', 'Motto'],
      ['established', 'Established'],
    ],
  },
  {
    title: 'Mission and vision',
    fields: [
      ['body', 'Body', true],
      ['mission', 'Mission', true],
      ['vision', 'Vision', true],
    ],
  },
  {
    title: 'History',
    fields: [['history', 'One item per line, Year|event', true]],
  },
  {
    title: 'Achievements',
    fields: [['achievements', 'One item per line', true]],
  },
  {
    title: 'Why choose us',
    fields: [['why_choose', 'One item per line, Title|description', true]],
  },
  {
    title: 'Call to action',
    fields: [
      ['cta_title', 'CTA title'],
      ['cta_body', 'CTA body'],
    ],
  },
];

function Field({ form, setForm, name, label, long }) {
  return (
    <label className="form-field">
      <span className="desk-line">
        <LineMark name="cms" size={14} />
        {label}
      </span>
      {long ? (
        <textarea rows={4} value={form[name] || ''} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />
      ) : (
        <input value={form[name] || ''} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />
      )}
    </label>
  );
}

const PAGE = {
  document: 'about',
  name: 'About page',
  saved: 'About page saved.',
  publishBody: 'The About page on the public website updates as soon as you confirm.',
};

export default function AdminCmsAboutPage() {
  const { publish, proposing } = useCmsPublish(PAGE);
  const [form, setForm] = useState(null);
  // The page as loaded, so a tagged editor's proposal carries only what changed.
  const [loaded, setLoaded] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCms()
      .then((data) => {
        const next = { ...DEFAULT_CMS.about, ...(data.about || {}) };
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

  if (loading) return <Loading label="Loading about copy…" />;
  if (!form) return error ? <p className="alert alert-error">{error}</p> : null;

  return (
    <form onSubmit={handleSave}>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}
      <div className="cms-grid-2">
        {GROUPS.map((group) => (
          <section className="card cms-card" key={group.title}>
            <h2 className="desk-line">
              <LineMark name="cms" />
              {group.title}
            </h2>
            {group.fields.map(([name, label, long]) => (
              <Field key={name} form={form} setForm={setForm} name={name} label={label} long={long} />
            ))}
          </section>
        ))}
      </div>
      <div className="cms-save">
        <button className="btn" type="submit">
          {proposing ? 'Submit for approval' : 'Save about'}
        </button>
      </div>
    </form>
  );
}
