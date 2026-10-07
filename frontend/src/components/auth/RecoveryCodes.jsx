import { useState } from 'react';

/** Recovery codes, shown once right after they are made. They are not kept anywhere in the browser. */
export default function RecoveryCodes({ codes }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(codes.join('\n'));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="recovery-codes" aria-labelledby="recovery-codes-title">
      <h3 id="recovery-codes-title">Save your recovery codes</h3>
      <p>
        Each code signs you in once if you lose your phone. Keep them somewhere safe and private, such as a printed
        copy in a locked drawer. They will not be shown again.
      </p>
      <ol>
        {codes.map((code) => (
          <li key={code}>
            <code>{code}</code>
          </li>
        ))}
      </ol>
      <button className="btn btn-secondary" type="button" onClick={copy}>
        {copied ? 'Copied' : 'Copy the codes'}
      </button>
    </section>
  );
}
