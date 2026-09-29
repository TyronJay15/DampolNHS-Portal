import { Link } from 'react-router-dom';

export default function AdvancedToolBanner({ workspacePath = '/head/sections' }) {
  return (
    <div className="studio-banner">
      <div>
        <strong>Advanced sectioning tool</strong>
        <p>Use Section Workspace for the guided setup process. This page is for direct bulk control.</p>
      </div>
      <Link className="btn btn-secondary" to={workspacePath}>
        Open Section Workspace
      </Link>
    </div>
  );
}
