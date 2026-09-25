import { useEffect, useState } from 'react';
import Navbar from '../../components/Navbar/Navbar';
import Footer from '../../components/Footer/Footer';
import Chatbot from '../../components/Chatbot/Chatbot';
import { fetchCms } from '../../services/publicService';
import { mergeCms } from '../../utils/cmsDefaults';

export default function PublicLayout({ children }) {
  const [cms, setCms] = useState(() => mergeCms({}));
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    fetchCms()
      .then((data) => {
        const next = mergeCms(data || {});
        setCms(next);
      })
      .catch(() => setCms(mergeCms({})));
  }, []);

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="public-shell">
      <Navbar isScrolled={isScrolled} logo={cms.footer?.logo} />
      <main className="site-main">{typeof children === 'function' ? children(cms) : children}</main>
      <Footer content={cms.footer} />
      <Chatbot />
    </div>
  );
}
