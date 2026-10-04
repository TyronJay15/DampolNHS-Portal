import { createContext, useContext } from 'react';

// Set by ProposalScope when an owner's page is opened by a tagged person: actions become requests.
export const ProposalContext = createContext(null);

// null on the owner's own screens; { activity, tag, ownerLabel, propose } in proposal mode.
export function useProposal() {
  return useContext(ProposalContext);
}
