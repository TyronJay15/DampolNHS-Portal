import { useState } from 'react';
import { askChatbot } from '../../services/publicService';
import './Chatbot.css';

const PROMPTS = ['How do I register?', 'What programs are offered?', 'When can I see my grades?'];

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Ask about registration, programs, login, grades, or contact information.' },
  ]);

  async function send(text) {
    const question = text.trim();
    if (!question || busy) return;
    setBusy(true);
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    try {
      const data = await askChatbot(question);
      setMessages((prev) => [...prev, { role: 'bot', text: data.answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'bot', text: err.message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`chatbot ${open ? 'is-open' : ''}`}>
      {open ? (
        <div className="chatbot-panel">
          <div className="chatbot-head">
            <strong>Portal assistant</strong>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </div>
          <div className="chatbot-messages">
            {messages.map((msg, index) => (
              <p key={`${index}-${msg.text.slice(0, 12)}`} className={`bubble bubble-${msg.role}`}>
                {msg.text}
              </p>
            ))}
          </div>
          <div className="chatbot-prompts">
            {PROMPTS.map((prompt) => (
              <button key={prompt} type="button" onClick={() => send(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
          <form
            className="chatbot-form"
            onSubmit={(event) => {
              event.preventDefault();
              send(input);
            }}
          >
            <input value={input} maxLength={400} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question" />
            <button className="btn" type="submit" disabled={busy}>
              Send
            </button>
          </form>
          <p className="chatbot-privacy">
            Please do not type your LRN, phone number, email or other personal details. Questions are kept for 90 days
            to improve the answers, and some are answered with Google Gemini.
          </p>
        </div>
      ) : null}
      <button type="button" className="chatbot-toggle" aria-label={open ? 'Close chat' : 'Open chat'} onClick={() => setOpen((v) => !v)}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8l-4 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 5v2h10V9H7zm0 4v2h7v-2H7z"
          />
        </svg>
      </button>
    </div>
  );
}
