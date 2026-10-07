import { useEffect, useState } from 'react';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import { formatDate } from '../../../components/Guidance/guidanceText';
import Icon from '../../../components/Icon/Icon';
import Loading from '../../../components/Loading/Loading';
import MetricStrip from '../../../components/MetricStrip/MetricStrip';
import { activateInstrument, fetchInstruments } from '../../../services/guidanceService';
import { firstApiError } from '../../../utils/authRules';

const TYPES = [
  ['R', 'Realistic'],
  ['I', 'Investigative'],
  ['A', 'Artistic'],
  ['S', 'Social'],
  ['E', 'Enterprising'],
  ['C', 'Conventional'],
];

function changed(question) {
  return question.text !== question.original_text;
}

// What must be true before students take the survey, in order.
function readiness(instrument) {
  return [
    { key: 'license', label: 'License terms confirmed', done: Boolean(instrument.license_confirmed_at) },
    { key: 'pilot', label: 'Piloted with Dampol students', done: instrument.pilot_status === 'piloted' },
    { key: 'open', label: 'Open to students', done: instrument.active },
  ];
}

function Questions({ questions }) {
  return (
    <div className="gd-question-groups">
      {TYPES.map(([code, name]) => {
        const rows = questions.filter((question) => question.riasec === code);
        if (!rows.length) return null;
        return (
          <section key={code} className="gd-question-group" aria-label={`${name} questions`}>
            <h4>
              <span className="gd-type-mark" aria-hidden="true">
                {code}
              </span>
              {name}
              <span className="gd-note">{rows.length}</span>
            </h4>
            <ol>
              {rows.map((question) => (
                <li key={question.id} value={question.position} className={changed(question) ? 'is-changed' : undefined}>
                  {question.text}
                  {changed(question) ? <small>Changed from the original: {question.change_note || 'see note'}</small> : null}
                </li>
              ))}
            </ol>
          </section>
        );
      })}
    </div>
  );
}

function Instrument({ instrument, busy, onOpen }) {
  const edited = instrument.questions.filter(changed).length;
  return (
    <section className="card gd-panel" aria-label={`${instrument.name} version ${instrument.version}`}>
      <div className="gd-section-head">
        <h3>
          {instrument.name} · version {instrument.version}
        </h3>
        {instrument.active ? (
          <span className="gd-pill is-strong">Open to students</span>
        ) : (
          <button className="btn" type="button" disabled={busy} onClick={() => onOpen(instrument)}>
            Review license and open
          </button>
        )}
      </div>

      <ul className="gd-checks gd-readiness" aria-label="Before students take it">
        {readiness(instrument).map((step) => (
          <li key={step.key} className={step.done ? 'is-ok' : 'is-no'}>
            <span className="gd-checks-mark">
              <Icon name={step.done ? 'check' : 'close'} size={14} />
            </span>
            <span>
              <strong>{step.label}</strong>
              {step.key === 'license' && step.done ? ` · ${formatDate(instrument.license_confirmed_at)}` : ''}
              {step.key === 'pilot' && !step.done ? ' · recommended before wide use' : ''}
            </span>
          </li>
        ))}
      </ul>

      <dl className="gd-facts">
        <div>
          <dt>Source</dt>
          <dd>
            <a href={instrument.source_url} target="_blank" rel="noopener noreferrer">
              {instrument.source}
            </a>
          </dd>
        </div>
        <div>
          <dt>License</dt>
          <dd>
            <a href={instrument.license_url} target="_blank" rel="noopener noreferrer">
              O*NET Career Exploration Tools license
            </a>
          </dd>
        </div>
        <div>
          <dt>Attribution shown to students</dt>
          <dd>{instrument.attribution}</dd>
        </div>
      </dl>

      <details className="gd-why">
        <summary>
          The {instrument.questions.length} questions by interest type
          {edited ? ` · ${edited} changed from the original` : ' · used unchanged'}
        </summary>
        <Questions questions={instrument.questions} />
      </details>
    </section>
  );
}

export default function GuidanceAssessmentPage() {
  const confirm = useConfirm();
  const [instruments, setInstruments] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchInstruments()
      .then((data) => setInstruments(data.instruments))
      .catch((err) => setError(err.message));
  }, []);

  async function activate(instrument) {
    const answer = await confirm({
      title: `Open ${instrument.name} v${instrument.version} to students?`,
      body: 'Confirm that the license terms were read and that the attribution below is shown to students. The items are used unchanged under CC BY-ND 4.0.',
      confirmLabel: 'Confirm license and open',
      facts: [
        { label: 'Questions', value: String(instrument.questions.length) },
        { label: 'Pilot', value: instrument.pilot_status === 'piloted' ? 'Piloted' : 'Not yet piloted' },
      ],
    });
    if (!answer) return;
    setBusy(true);
    setError('');
    try {
      setInstruments((await activateInstrument(instrument.id)).instruments);
    } catch (err) {
      setError(firstApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!instruments && !error) return <Loading label="Loading the assessment…" />;

  const open = (instruments || []).find((instrument) => instrument.active);
  return (
    <>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {instruments ? (
        <MetricStrip
          items={[
            { key: 'status', label: 'Students can take it', value: open ? 'Yes' : 'Not yet', icon: 'guidance', tone: open ? 'green' : 'gold' },
            { key: 'version', label: 'Open version', value: open ? `v${open.version}` : '—', icon: 'history', tone: 'blue' },
            { key: 'questions', label: 'Questions', value: open ? open.questions.length : '—', icon: 'grades', tone: 'purple' },
            {
              key: 'pilot',
              label: 'Pilot',
              value: open?.pilot_status === 'piloted' ? 'Done' : 'Not yet',
              icon: 'check',
              tone: open?.pilot_status === 'piloted' ? 'green' : 'gold',
            },
          ]}
        />
      ) : null}
      {(instruments || []).map((instrument) => (
        <Instrument key={instrument.id} instrument={instrument} busy={busy} onOpen={activate} />
      ))}
    </>
  );
}
