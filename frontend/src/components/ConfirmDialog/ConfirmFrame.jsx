import { useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import Icon from '../Icon/Icon';
import './ConfirmDialog.css';
import { useDialogBehavior } from './useDialogBehavior';

const TONE_ICON = { standard: 'approve', warning: 'alert', danger: 'trash' };
const THEME_KEY = 'dampol-theme';

function activeTheme() {
  try {
    return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

// The shell shared by every confirmation: overlay, panel, header and action row, plus the focus and
// keyboard behavior. ConfirmDialog fills it for the common cases; ConfirmDeleteModal fills it with
// its typed-confirmation form. Mark the element that should get focus first with data-autofocus.
export default function ConfirmFrame({
  title,
  tone = 'standard',
  icon,
  wide = false,
  dismissable = tone !== 'danger',
  onDismiss,
  actions,
  children,
}) {
  const panel = useRef(null);
  const titleId = useId();

  const handleKeyDown = useDialogBehavior(panel, onDismiss);

  return createPortal(
    <div
      className="cfm"
      data-theme={activeTheme()}
      onMouseDown={(event) => {
        if (dismissable && event.target === event.currentTarget) onDismiss?.();
      }}
      onKeyDown={handleKeyDown}
    >
      <div
        ref={panel}
        className={`cfm-panel is-${tone}${wide ? ' is-wide' : ''}`}
        role={tone === 'danger' ? 'alertdialog' : 'dialog'}
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="cfm-head">
          <span className="cfm-badge" aria-hidden="true">
            <Icon name={icon || TONE_ICON[tone]} size={20} />
          </span>
          <h2 id={titleId}>{title}</h2>
        </header>
        {children}
        <footer className="cfm-actions">{actions}</footer>
      </div>
    </div>,
    document.body,
  );
}
