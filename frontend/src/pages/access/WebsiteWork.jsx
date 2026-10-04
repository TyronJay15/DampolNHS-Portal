import { useState } from 'react';
import { useProposal } from '../../components/Access/proposalContext';
import AdminCmsAboutPage from '../admin/cms/AdminCmsAboutPage';
import AdminCmsContactPage from '../admin/cms/AdminCmsContactPage';
import AdminCmsFooterPage from '../admin/cms/AdminCmsFooterPage';
import AdminCmsLandingPage from '../admin/cms/AdminCmsLandingPage';
import './WebsiteWork.css';

const PAGES = [
  { key: 'landing', label: 'Landing', Page: AdminCmsLandingPage },
  { key: 'about', label: 'About', Page: AdminCmsAboutPage },
  { key: 'contact', label: 'Contact', Page: AdminCmsContactPage },
  { key: 'footer', label: 'Footer', Page: AdminCmsFooterPage },
];

// The website pages a tagged editor may propose changes to: only the page their tag covers, or all four.
export default function WebsiteWork() {
  const { tag } = useProposal();
  const pages = PAGES.filter((page) => !tag.scope || page.key === tag.scope);
  const [current, setCurrent] = useState(pages[0].key);
  const { Page } = pages.find((page) => page.key === current);

  return (
    <>
      {pages.length > 1 ? (
        <nav className="cms-tabs website-work-tabs" aria-label="Website pages">
          {pages.map((page) => (
            <button
              key={page.key}
              type="button"
              className={`cms-tab${page.key === current ? ' is-active' : ''}`}
              aria-current={page.key === current ? 'page' : undefined}
              onClick={() => setCurrent(page.key)}
            >
              {page.label}
            </button>
          ))}
        </nav>
      ) : null}
      <Page key={current} />
    </>
  );
}
