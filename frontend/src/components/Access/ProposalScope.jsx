import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { submitAccessRequest } from '../../services/accessService';
import { useConfirm } from '../ConfirmDialog/useConfirm';
import { ProposalContext } from './proposalContext';
import './ProposalScope.css';

// Wraps an owner's page for a tagged person. Nothing changes until the owner approves: each action
// asks for a note, then becomes an access request. propose() resolves to the request, or null if cancelled.
// payload may be a function of the note, for a request whose reason is the note itself (e.g. a rejection).
export default function ProposalScope({ activity, tag, ownerLabel, myAccessPath, children }) {
  const confirm = useConfirm();

  const value = useMemo(
    () => ({
      activity,
      tag,
      ownerLabel,
      async propose(payload, { title, body, facts, warning, noteLabel }) {
        const answer = await confirm({
          title,
          body: body || `This is sent to the ${ownerLabel} for approval. Nothing changes until it is approved.`,
          confirmLabel: 'Submit for approval',
          facts,
          warning,
          note: {
            label: noteLabel || `Note for the ${ownerLabel}`,
            placeholder: 'Why should this be approved?',
            required: true,
            maxLength: 1000,
          },
        });
        if (!answer) return null;
        const proposal = typeof payload === 'function' ? payload(answer.note) : payload;
        return submitAccessRequest({ activity, payload: proposal, note: answer.note });
      },
    }),
    [activity, tag, ownerLabel, confirm],
  );

  return (
    <ProposalContext.Provider value={value}>
      <p className="proposal-banner" role="note">
        <strong>Preparing for approval.</strong> Your changes are sent to the {ownerLabel} as requests; nothing changes
        until they approve. <Link to={myAccessPath}>See my requests</Link>
      </p>
      {children}
    </ProposalContext.Provider>
  );
}
