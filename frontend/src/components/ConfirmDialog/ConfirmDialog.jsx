import { useState } from 'react';
import Icon from '../Icon/Icon';
import ConfirmFrame from './ConfirmFrame';

// The common confirmation: body text, optional count tiles, warning panel and note box.
// Pages never render it: they call useConfirm() (see ConfirmProvider).
// onResolve receives { note } when confirmed and null when cancelled.
export default function ConfirmDialog({ options, onResolve }) {
  const {
    title,
    body,
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    tone = 'standard',
    icon,
    facts,
    warning,
    note,
  } = options;
  const [text, setText] = useState(note?.initial || '');
  const warnings = [].concat(warning || []);
  const blocked = Boolean(note?.required) && !text.trim();
  // Where focus lands first: the note box, else Cancel for danger, else the confirm button.
  const first = note ? 'note' : tone === 'danger' ? 'cancel' : 'confirm';
  const autofocus = (name) => (name === first ? '' : undefined);

  return (
    <ConfirmFrame
      title={title}
      tone={tone}
      icon={icon}
      onDismiss={() => onResolve(null)}
      actions={
        <>
          {cancelLabel === null ? null : (
            <button type="button" className="cfm-btn is-cancel" onClick={() => onResolve(null)} data-autofocus={autofocus('cancel')}>
              {cancelLabel}
            </button>
          )}
          <button
            type="button"
            className="cfm-btn is-confirm"
            disabled={blocked}
            onClick={() => onResolve({ note: text.trim() })}
            data-autofocus={autofocus('confirm')}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      {body ? <div className="cfm-body">{body}</div> : null}

      {facts?.length ? (
        <dl className="cfm-facts">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dd>{fact.value}</dd>
              <dt>{fact.label}</dt>
            </div>
          ))}
        </dl>
      ) : null}

      {warnings.length ? (
        <div className="cfm-warning" role="note">
          <Icon name="alert" size={16} />
          <div>
            {warnings.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        </div>
      ) : null}

      {note ? (
        <label className="cfm-field">
          <span>
            {note.label || 'Note'}
            {note.required ? '' : ' (optional)'}
          </span>
          <textarea
            data-autofocus={autofocus('note')}
            rows={3}
            value={text}
            maxLength={note.maxLength || 255}
            placeholder={note.placeholder || ''}
            onChange={(event) => setText(event.target.value)}
          />
        </label>
      ) : null}
    </ConfirmFrame>
  );
}
