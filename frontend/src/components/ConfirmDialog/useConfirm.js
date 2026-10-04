import { useContext } from 'react';
import { ConfirmContext } from './confirmContext';

// const confirm = useConfirm();
// const answer = await confirm({ title, body, confirmLabel, cancelLabel, tone, icon, facts, warning, note });
//   answer === null           the user cancelled
//   answer.note               the note text (when a note field was requested; '' when left empty)
//   tone                      'standard' | 'warning' | 'danger'
//   facts                     [{ label, value }] shown as count tiles
//   warning                   a string or list of strings shown in a gold panel
//   note                      { label, placeholder, required, maxLength } adds a text box
export function useConfirm() {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error('useConfirm must be used inside ConfirmProvider');
  return confirm;
}
