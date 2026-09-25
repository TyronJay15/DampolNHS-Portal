import { useEffect, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import { fetchCms, saveCmsDocument } from '../../../services/cmsService';
import { DEFAULT_CMS } from '../../../utils/cmsDefaults';
import './AdminCms.css';

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

export default function AdminCmsAboutPage() {
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCms()
      .then((data) => setForm({ ...DEFAULT_CMS.about, ...(data.about || {}) }))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setError('');
    try {
      await saveCmsDocument('about', form);
      setMessage('About page saved.');
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
          Save about
        </button>
      </div>
    </form>
  );
}
