import { Link } from 'react-router-dom';
import AuthShell from './AuthShell';
import './RegistrationWaitingPage.css';

export default function RegistrationWaitingPage() {
  return (
    <AuthShell title="Registration received" className="waiting-page">
      <p className="waiting-lead">
        Thank you for registering with Dampol 1st National High School. Your application is on file,
        but you cannot sign in until an administrator reviews and approves it.
      </p>
      <p className="waiting-lead">Nothing more is needed from you right now. Keep your LRN and password ready.</p>
      <ol className="waiting-steps">
        <li>Wait for the school office to review the registration.</li>
        <li>After approval, sign in with your LRN and password.</li>
        <li>If you need help, contact the school office.</li>
      </ol>
      <div className="auth-foot">
        <Link className="btn" to="/login">
          Go to login
        </Link>
        <Link className="btn btn-ghost" to="/contact">
          Contact the school
        </Link>
        <Link className="btn btn-ghost" to="/">
          ← Back to Home
        </Link>
      </div>
    </AuthShell>
  );
}
