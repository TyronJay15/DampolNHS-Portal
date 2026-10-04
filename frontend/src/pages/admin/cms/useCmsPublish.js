import { useProposal } from '../../../components/Access/proposalContext';
import { useConfirm } from '../../../components/ConfirmDialog/useConfirm';
import { saveCmsDocument } from '../../../services/cmsService';

// Top-level fields whose value differs between the page as loaded and as edited.
function changedFields(loaded, form) {
  return Object.fromEntries(
    Object.keys(form)
      .filter((key) => JSON.stringify(form[key]) !== JSON.stringify(loaded?.[key]))
      .map((key) => [key, form[key]]),
  );
}

// Saving one CMS page. The Admin publishes the whole page; a person tagged to edit website pages
// sends only the changed fields for the Admin's approval. publish() resolves to the message to show,
// or '' when cancelled, and throws on errors; proposing is true for the tagged editor.
// `page` is { document, name, saved, publishBody }.
export function useCmsPublish(page) {
  const confirm = useConfirm();
  const proposal = useProposal();

  async function publish(form, loaded) {
    if (proposal) {
      const changes = changedFields(loaded, form);
      if (!Object.keys(changes).length) throw new Error('Nothing has changed yet.');
      const sent = await proposal.propose(
        { document: page.document, changes },
        {
          title: `Propose changes to the ${page.name}?`,
          facts: [{ label: 'Changed sections', value: Object.keys(changes).length }],
        },
      );
      return sent ? 'Sent to the Admin for approval. Follow it under My access.' : '';
    }
    const answer = await confirm({
      title: `Publish changes to the ${page.name}?`,
      body: page.publishBody,
      confirmLabel: 'Publish changes',
    });
    if (!answer) return '';
    await saveCmsDocument(page.document, form);
    return page.saved;
  }

  return { publish, proposing: Boolean(proposal) };
}
