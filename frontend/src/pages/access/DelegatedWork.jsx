import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ProposalScope from '../../components/Access/ProposalScope';
import Loading from '../../components/Loading/Loading';
import PageHead from '../../components/PageHead/PageHead';
import { fetchAccessOverview } from '../../services/accessService';
import AdminAccountsPage from '../admin/AdminAccountsPage';
import '../admin/AdminAccountsPage.css';
import AdminCmsNewsPage from '../admin/cms/AdminCmsNewsPage';
import AdminCmsProgramsPage from '../admin/cms/AdminCmsProgramsPage';
import '../admin/cms/AdminCms.css';
import HeadAssignPage from '../head/HeadAssignPage';
import HeadCorrectionsPage from '../head/HeadCorrectionsPage';
import HeadPlacePage from '../head/HeadPlacePage';
import HeadTermPlanPage from '../head/HeadTermPlanPage';
import WebsiteWork from './WebsiteWork';

// The owner's own page for each piece of work, opened in proposal mode (see activities.py on the server).
// The Admin pages normally get their heading from an Admin layout, so `frame` supplies it here.
const WORK = {
  registrations: {
    activity: 'review_registrations',
    owner: 'Admin',
    Page: AdminAccountsPage,
    frame: { className: 'desk admin-accounts', title: 'Review registrations', icon: 'user' },
  },
  programs: {
    activity: 'edit_programs',
    owner: 'Admin',
    Page: AdminCmsProgramsPage,
    frame: { className: 'desk admin-cms', title: 'Edit programs', icon: 'cms' },
  },
  website: {
    activity: 'edit_website_pages',
    owner: 'Admin',
    Page: WebsiteWork,
    frame: { className: 'desk admin-cms', title: 'Edit website pages', icon: 'cms' },
  },
  news: {
    activity: 'post_news',
    owner: 'Admin',
    Page: AdminCmsNewsPage,
    frame: { className: 'desk admin-cms', title: 'Post news & events', icon: 'cms' },
  },
  placements: { activity: 'prepare_placements', owner: 'Head Teacher', Page: HeadPlacePage },
  'term-plan': { activity: 'prepare_term_plan', owner: 'Head Teacher', Page: HeadTermPlanPage },
  assignments: { activity: 'prepare_assignments', owner: 'Head Teacher', Page: HeadAssignPage },
  corrections: { activity: 'review_corrections', owner: 'Head Teacher', Page: HeadCorrectionsPage },
};

export default function DelegatedWork({ myAccessPath }) {
  const { work } = useParams();
  const entry = WORK[work];
  // The person's live tag for this work (its scope limits what they see), or false when they have none.
  const [tag, setTag] = useState(null);

  useEffect(() => {
    if (!entry) return;
    fetchAccessOverview()
      .then((data) => setTag(data.holds.find((row) => row.activity === entry.activity) || false))
      .catch(() => setTag(false));
  }, [entry]);

  if (entry && tag === null) return <Loading label="Checking your access…" />;
  if (!entry || !tag) {
    return (
      <div className="desk studio">
        <p className="card studio-panel studio-empty">
          You do not have an active tag for this work. <Link to={myAccessPath}>See my access</Link>
        </p>
      </div>
    );
  }
  const { Page, frame } = entry;
  const scoped = (
    <ProposalScope activity={entry.activity} tag={tag} ownerLabel={entry.owner} myAccessPath={myAccessPath}>
      <Page />
    </ProposalScope>
  );
  if (!frame) return scoped;
  return (
    <div className={frame.className}>
      <PageHead kicker="Delegated work" title={frame.title} icon={frame.icon} />
      {scoped}
    </div>
  );
}
