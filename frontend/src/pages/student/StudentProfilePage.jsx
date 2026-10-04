import { useEffect, useState } from 'react';
import Loading from '../../components/Loading/Loading';
import LineMark from '../../components/LineMark/LineMark';
import MoreMenu from '../../components/MoreMenu/MoreMenu';
import PageHead from '../../components/PageHead/PageHead';
import { fetchStudentMe, updateStudentMe } from '../../services/studentService';
import { firstApiError } from '../../utils/authRules';
import { GENDER_OPTIONS, genderLabel } from '../../utils/gender';
import './StudentStudio.css';

function kindLabel(kind) {
  return kind ? kind.replaceAll('_', ' ') : '—';
}

function termsLabel(terms) {
  if (!terms?.length || terms.length === 3) return 'All terms';
  return `Term ${terms.join(' & ')}`;
}

function formatBirthdate(value) {
  if (!value) return '—';
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
}

function initials(me) {
  return `${me?.first_name?.[0] || ''}${me?.last_name?.[0] || ''}`.toUpperCase() || 'ST';
}

function contactForm(me) {
  return {
    contact_number: me?.contact_number || '',
    gender: me?.gender || '',
    address: me?.address || '',
    guardian_name: me?.guardian_name || '',
    guardian_contact: me?.guardian_contact || '',
  };
}

export default function StudentProfilePage() {
  const [me, setMe] = useState(null);
  const [form, setForm] = useState(contactForm(null));
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchStudentMe()
      .then((profile) => {
        setMe(profile);
        setForm(contactForm(profile));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setSaved('');
    try {
      const profile = await updateStudentMe(form);
      setMe(profile);
      setForm(contactForm(profile));
      setSaved('Details saved. Admin and your adviser can see the update.');
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading your profile…" />;

  return (
    <div className="desk student-studio">
      <PageHead kicker="Enrollment record" title="My Profile" icon="user">
        <p>Identity stays with the school. You can update your contact details, gender and guardian anytime.</p>
      </PageHead>
      <MoreMenu items={[{ to: '/print/grades', label: 'Print grades' }]} />
      {error ? <p className="alert alert-error">{error}</p> : null}
      {saved ? <p className="alert alert-info">{saved}</p> : null}

      <div className="student-profile-grid">
        <section className="card student-panel">
          <div className="student-identity">
            <span className="student-avatar">{initials(me)}</span>
            <div>
              <h2>
                <LineMark name="user" />
                Identity
              </h2>
              <p className="student-empty">Name, LRN, and email cannot be edited here.</p>
            </div>
          </div>
          <dl className="student-facts">
            <div>
              <dt className="desk-line">
                <LineMark name="user" size={14} />
                Name
              </dt>
              <dd>
                {me?.first_name} {me?.middle_name} {me?.last_name}
              </dd>
            </div>
            <div>
              <dt className="desk-line">
                <LineMark name="grades" size={14} />
                LRN
              </dt>
              <dd>{me?.lrn || '—'}</dd>
            </div>
            <div>
              <dt className="desk-line">
                <LineMark name="mail" size={14} />
                Email
              </dt>
              <dd>{me?.email || '—'}</dd>
            </div>
            <div>
              <dt className="desk-line">
                <LineMark name="year" size={14} />
                Birthdate
              </dt>
              <dd>{formatBirthdate(me?.birthdate)}</dd>
            </div>
            <div>
              <dt className="desk-line">
                <LineMark name="user" size={14} />
                Gender
              </dt>
              <dd>{genderLabel(me?.gender)}</dd>
            </div>
            <div>
              <dt className="desk-line">
                <LineMark name="sections" size={14} />
                Program
              </dt>
              <dd>{me?.section?.program || me?.program || '—'}</dd>
            </div>
          </dl>
        </section>

        <section className="card student-panel">
          <h2>
            <LineMark name="sections" />
            Section
          </h2>
          {me?.section ? (
            <dl className="student-facts">
              <div>
                <dt className="desk-line">
                  <LineMark name="sections" size={14} />
                  Section
                </dt>
                <dd>{me.section.name}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="classes" size={14} />
                  Grade
                </dt>
                <dd>{me.section.grade_level || me?.grade_level || '—'}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="year" size={14} />
                  School year
                </dt>
                <dd>{me.section.school_year}</dd>
              </div>
              <div>
                <dt className="desk-line">
                  <LineMark name="advisory" size={14} />
                  Adviser
                </dt>
                <dd>{me.section.adviser || 'Not assigned yet'}</dd>
              </div>
            </dl>
          ) : (
            <p className="student-empty">You have not been assigned a section yet.</p>
          )}
        </section>
      </div>

      <section className="card student-panel">
        <h2>
          <LineMark name="phone" />
          Details you can update
        </h2>
        <p className="student-empty">Admin and your adviser see these values. Subject teachers keep the encode list to name and LRN.</p>
        <form className="student-form" onSubmit={save}>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="phone" size={14} />
              Contact number
            </span>
            <input
              required
              value={form.contact_number}
              onChange={(event) => {
                const value = event.target.value;
                if (value && /[^0-9]/.test(value)) return;
                update('contact_number', value);
              }}
              inputMode="numeric"
              maxLength={11}
              placeholder="09XXXXXXXXX"
            />
          </label>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="phone" size={14} />
              Guardian contact
            </span>
            <input
              value={form.guardian_contact}
              onChange={(event) => {
                const value = event.target.value;
                if (value && /[^0-9]/.test(value)) return;
                update('guardian_contact', value);
              }}
              inputMode="numeric"
              maxLength={11}
              placeholder="09XXXXXXXXX"
            />
          </label>
          <label className="form-field is-wide">
            <span className="desk-line">
              <LineMark name="home" size={14} />
              Address
            </span>
            <input
              required
              value={form.address}
              onChange={(event) => update('address', event.target.value)}
              placeholder="House, barangay, municipality"
            />
          </label>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="user" size={14} />
              Gender
            </span>
            <select required value={form.gender} onChange={(event) => update('gender', event.target.value)}>
              <option value="">Select gender</option>
              {GENDER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="desk-line">
              <LineMark name="guardian" size={14} />
              Guardian name
            </span>
            <input
              value={form.guardian_name}
              onChange={(event) => update('guardian_name', event.target.value)}
              placeholder="Parent or guardian"
            />
          </label>
          <div className="student-form-actions">
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Saving…' : 'Save details'}
            </button>
          </div>
        </form>
      </section>

      <section className="card student-panel">
        <h2>
          <LineMark name="classes" />
          Program subjects
        </h2>
        {me?.subjects?.length ? (
          <div className="student-subject-wrap">
            <table className="student-subject-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Type</th>
                  <th>Term</th>
                </tr>
              </thead>
              <tbody>
                {me.subjects.map((row) => (
                  <tr key={row.code || row.id || row.name}>
                    <td>
                      <span className="desk-line">
                        <LineMark name="classes" size={14} />
                        {row.name}
                      </span>
                    </td>
                    <td>{kindLabel(row.kind)}</td>
                    <td>{termsLabel(row.terms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="student-empty">Your program subjects will appear after enrollment.</p>
        )}
      </section>
    </div>
  );
}
