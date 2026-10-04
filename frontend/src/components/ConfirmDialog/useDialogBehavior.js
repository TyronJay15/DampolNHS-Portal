import { useEffect } from 'react';

const FOCUSABLE = 'button:not([disabled]), textarea, input, select, a[href], [tabindex]:not([tabindex="-1"])';

// Shared modal behavior: focus the element marked data-autofocus (else the first control), keep Tab
// inside the panel, close on Escape, lock page scroll, and give focus back to whatever opened it.
// Returns the keydown handler to put on the overlay.
export function useDialogBehavior(panelRef, onDismiss) {
  useEffect(() => {
    const opener = document.activeElement;
    const panel = panelRef.current;
    const start = panel?.querySelector('[data-autofocus]') || panel?.querySelector(FOCUSABLE);
    start?.focus();
    const scroll = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = scroll;
      opener?.focus?.();
    };
  }, [panelRef]);

  return function handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onDismiss?.();
      return;
    }
    if (event.key !== 'Tab') return;
    const items = [...panelRef.current.querySelectorAll(FOCUSABLE)];
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
}
