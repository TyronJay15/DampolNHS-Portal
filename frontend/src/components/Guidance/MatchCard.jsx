import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import MatchLabel from './MatchLabel';
import { INTEREST_WORDS, grade, gradeWidth, scoreWidth, strandText } from './guidanceText';

function Bar({ label, value, width }) {
  return (
    <div className="gd-bar-row">
      <span>{label}</span>
      <span className="gd-bar" aria-hidden="true">
        <i style={{ width: `${width}%` }} />
      </span>
      <b>{value}</b>
    </div>
  );
}

// One primary recommendation: the evidence behind it and the actions a student can take.
export default function MatchCard({ item, programPath, compare }) {
  const [open, setOpen] = useState(false);
  const whyId = useId();
  const { evidence, program } = item;
  const strengths = (evidence.strengths || []).slice(0, 3);
  const interest = evidence.interest;
  const strand = strandText(evidence.strand);
  const below = evidence.below_benchmark?.[0];
  const picked = compare?.codes.includes(program.code);

  return (
    <article className="gd-card">
      <div className="gd-card-head">
        <span className="gd-rank" aria-label={`Rank ${item.rank}`}>
          {item.rank}
        </span>
        <div>
          <h3>{program.name}</h3>
          <span className="gd-card-family">{program.family || 'Program family pending'}</span>
        </div>
      </div>
      <div className="gd-card-label">
        <MatchLabel label={item.label} />
      </div>
      <div className="gd-card-body">
        <h5>Why this matches you</h5>
        {strengths.map((row) => (
          <Bar key={row.key} label={row.label} value={grade(row.student)} width={gradeWidth(row.student)} />
        ))}
        {interest ? (
          <Bar
            label="Interest"
            value={INTEREST_WORDS[interest.tier] || '—'}
            width={scoreWidth(interest.score)}
          />
        ) : (
          <p className="gd-note">Interest not assessed yet.</p>
        )}
        {strand ? <p className="gd-note">Strand: {strand}</p> : null}
        {below ? (
          <p className="gd-note">
            {below.label} {grade(below.student)} is below the {below.official ? 'official requirement' : 'profile benchmark'} of{' '}
            {grade(below.benchmark)}. {below.official ? '' : 'It stays on your list.'}
          </p>
        ) : null}
      </div>
      {open ? (
        <ul className="gd-card-why" id={whyId}>
          {item.explanation.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      <div className="gd-card-foot">
        {programPath ? (
          <Link className="btn" to={`${programPath}/${program.code}`}>
            View program
          </Link>
        ) : null}
        <button
          className="btn btn-secondary"
          type="button"
          aria-expanded={open}
          aria-controls={whyId}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? 'Hide why' : 'Why this?'}
        </button>
        {compare ? (
          <button
            className="btn btn-secondary"
            type="button"
            aria-pressed={picked}
            disabled={!picked && compare.full}
            onClick={() => compare.toggle(program.code)}
          >
            {picked ? 'Picked to compare' : 'Compare'}
          </button>
        ) : null}
      </div>
    </article>
  );
}
