import { useEffect, useState } from 'react';
import LineMark from '../../../components/LineMark/LineMark';
import Loading from '../../../components/Loading/Loading';
import FieldLabel from './FieldLabel';
import { fetchCms, saveCmsDocument } from '../../../services/cmsService';
import { DEFAULT_CMS } from '../../../utils/cmsDefaults';
import './AdminCms.css';

const GROUPS = [
  {
    title: 'School details',
    fields: [
      ['title', 'Title'],
      ['subtitle', 'Subtitle'],
      ['description', 'Description', true],
      ['address', 'Address'],
      ['email', 'Email'],
      ['phone', 'Phone'],
    ],
  },
  {
    title: 'Hours and links',
    fields: [
      ['hours', 'Office hours'],
      ['facebook_url', 'Facebook URL'],
      ['deped_url', 'DepEd URL'],
    ],
  },
];

export default function AdminCmsContactPage() {
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCms()
      .then((data) => setForm({ ...DEFAULT_CMS.contact, ...(data.contact || {}) }))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setError('');
    try {
      await saveCmsDocument('contact', form);
      setMessage('Contact page saved.');
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading label="Loading contact copy…" />;
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
              <label className="form-field" key={name}>
                <FieldLabel>{label}</FieldLabel>
                {long ? (
                  <textarea
                    rows={4}
                    value={form[name] || ''}
                    onChange={(event) => setForm({ ...form, [name]: event.target.value })}
                  />
                ) : (
                  <input value={form[name] || ''} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />
                )}
              </label>
            ))}
          </section>
        ))}
      </div>
      <div className="cms-save">
        <button className="btn" type="submit">
          Save contact
        </button>
      </div>
    </form>
  );
}
