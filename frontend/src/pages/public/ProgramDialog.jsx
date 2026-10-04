import { useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { useDialogBehavior } from '../../components/ConfirmDialog/useDialogBehavior';
import { ArrowIcon, CapIcon } from '../../components/icons/SchoolIcons';

// Subjects are grouped in this order; anything without a type is listed under "Subjects".
const KIND_GROUPS = [
  ['core', 'Core subjects'],
  ['applied', 'Applied subjects'],
  ['specialized', 'Specialized subjects'],
  ['elective', 'Electives'],
  ['', 'Subjects'],
];

function kindOf(subject) {
  return KIND_GROUPS.some(([kind]) => kind === subject.kind) ? subject.kind : '';
}

function subjectGroups(subjects) {
  return KIND_GROUPS.map(([kind, label]) => ({ label, items: subjects.filter((subject) => kindOf(subject) === kind) })).filter(
    (group) => group.items.length,
  );
}

// The details of one program as a pop-up card, with the way to apply.
export default function ProgramDialog({ program, onClose }) {
  const panel = useRef(null);
  const titleId = useId();
  const handleKeyDown = useDialogBehavior(panel, onClose);
  const groups = subjectGroups(program.subjects || []);
  const pathways = program.pathways || [];
  const badges = [program.grade_level, program.track, program.curriculum].filter(Boolean);

  return createPortal(
    <div
      className="pd"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={handleKeyDown}
    >
      <article ref={panel} className="pd-panel" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header className="pd-head">
          <span className="pd-mark" aria-hidden="true">
            <CapIcon />
          </span>
          <div className="pd-title">
            <h2 id={titleId}>{program.code}</h2>
            {program.name && program.name !== program.code ? <p>{program.name}</p> : null}
            {badges.length ? (
              <ul className="pd-badges" aria-label="Program facts">
                {badges.map((badge) => (
                  <li key={badge}>{badge}</li>
                ))}
              </ul>
            ) : null}
          </div>
          <button className="pd-close" type="button" onClick={onClose} aria-label="Close details" data-autofocus="">
            ×
          </button>
        </header>

        <div className="pd-body">
          {program.description || program.summary ? (
            <p className="pd-description">{program.description || program.summary}</p>
          ) : null}
          <div className="pd-columns">
            {groups.length ? (
              <section>
                <h3>What you will study</h3>
                {groups.map((group) => (
                  <div className="pd-group" key={group.label}>
                    <h4>{group.label}</h4>
                    <ul>
                      {group.items.map((subject) => (
                        <li key={subject.code || subject.name}>{subject.name}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </section>
            ) : null}
            {pathways.length ? (
              <section>
                <h3>Where it can lead</h3>
                <ul className="pd-pathways">
                  {pathways.map((pathway) => (
                    <li key={pathway}>{pathway}</li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        </div>

        <footer className="pd-actions">
          <button className="btn btn-secondary" type="button" onClick={onClose}>
            Close
          </button>
          <Link className="btn" to={`/register?program=${encodeURIComponent(program.code)}`}>
            Apply to this program <ArrowIcon />
          </Link>
        </footer>
      </article>
    </div>,
    document.body,
  );
}
