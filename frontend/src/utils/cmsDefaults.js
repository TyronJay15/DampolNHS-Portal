export const DEFAULT_CMS = {
  landing: {
    slides: [
      {
        id: 'slide-1',
        kicker: 'Dampol 1st National High School',
        title: 'Learning Today. Leading Tomorrow.',
        body: 'A home for growth, discipline, and excellence — built with the community.',
        image: '/landingpage/damo.jpg',
        ctaPrimary: { to: '/register', label: 'Enroll / Register' },
        ctaSecondary: { to: '/about', label: 'Learn more' },
      },
      {
        id: 'slide-2',
        kicker: 'Programs & Activities',
        title: 'Developing Skills Beyond the Classroom',
        body: 'Student clubs, leadership, and community programs that strengthen character.',
        image: '/landingpage/dammo2.jpg',
        ctaPrimary: { to: '/programs', label: 'View programs' },
        ctaSecondary: { to: '/contact', label: 'Contact us' },
      },
      {
        id: 'slide-3',
        kicker: 'Announcements',
        title: 'Stay Updated With School News',
        body: 'Upcoming events, important notices, and school-wide updates — all in one place.',
        image: '/landingpage/damo3.jpg',
        ctaPrimary: { to: '/announcements', label: 'Read news' },
        ctaSecondary: { to: '/login', label: 'Sign in' },
      },
      {
        id: 'slide-4',
        kicker: 'Dampol 1st National High School',
        title: 'Welcome to Dampol 1st National High School',
        body: 'A glimpse of our campus — where learning and community meet.',
        image: '/landingpage/dampolzz.jpg',
        ctaPrimary: { to: '/register', label: 'Register now' },
        ctaSecondary: { to: '/about', label: 'About the school' },
      },
    ],
    aboutSection: {
      title: 'About Dampol 1st',
      subtitle: 'What we do, what we believe in, and how we serve our learners and community.',
    },
    aboutCards: [
      {
        id: 'lp-mission',
        title: 'Mission',
        body: 'Provide quality education that develops students holistically and prepares them for life-long learning.',
        image: '/logo/logodampol.jpg',
        linkTo: '/about',
        cta: 'Read mission',
      },
      {
        id: 'lp-vision',
        title: 'Vision',
        body: 'Produce globally competitive, morally upright, and socially responsible citizens.',
        image: '/logo/logodampol.jpg',
        linkTo: '/about',
        cta: 'Read vision',
      },
      {
        id: 'lp-values',
        title: 'Core Values',
        body: 'Respect, discipline, excellence, and service — guided by our community and shared goals.',
        image: '/logo/logodampol.jpg',
        linkTo: '/about',
        cta: 'See values',
      },
    ],
    bulletinSection: {
      title: 'Campus Bulletin',
      subtitle: 'Updates about school activities, student life, and important notices.',
    },
    banner: {
      schoolTitle: 'DAMPOL 1ST NATIONAL HIGH SCHOOL',
      admissionText: 'Now Accepting Admissions for S.Y. 2025-2026',
      description: 'Enroll today and discover a world of learning, growth, and endless possibilities.',
      logo: '/logo/logodampol.jpg',
    },
  },
  about: {
    title: 'About Our School',
    subtitle: 'Excellence in education in Pulilan, Bulacan.',
    body: 'Dampol 1st National High School is committed to providing quality education and shaping the future of our students.',
    established: '1965',
    motto: 'Thy Light Shall Guide Us!',
    vision:
      'To be a leading educational institution that produces globally competitive, morally upright, and socially responsible citizens.',
    mission:
      'To provide quality education that develops the intellectual, physical, social, and spiritual aspects of every student, preparing them for life-long learning and responsible citizenship.',
    history:
      '1965|Dampol 1st National High School was established in Pulilan, Bulacan.\n|The school later became a National High School.\n|Senior High School programs opened to prepare students for college, work, and community life.',
    achievements:
      'Recognition as a National High School\nParticipation in academic competitions\nPartnerships with the local community and partner agencies',
    why_choose:
      'Dedicated teachers|Learners study with teachers who are committed to student growth.\nSenior High School programs|A complete Senior High School offering for college, work, and community life.\nSupportive campus|A campus that values respect, discipline, excellence, and service.',
    cta_title: 'Join our community',
    cta_body: 'Register for the next school year, or contact the school office.',
  },
  contact: {
    title: 'Contact Us',
    subtitle: 'We are here to help students, parents, and visitors.',
    description: 'Visit the school office or use the official channels below.',
    address: 'Dampol 1st, Pulilan, Bulacan, Philippines',
    email: 'info@dampol1nhs.edu.ph',
    phone: '(044) 123-4567',
    hours: 'Monday - Friday: 7:00 AM - 5:00 PM',
    deped_url: 'https://www.deped.gov.ph/',
    facebook_url: 'https://www.facebook.com/D1stNHS/',
  },
  footer: {
    brandName: 'Dampol 1st National High School',
    brandTagline: 'School Portal',
    logo: '/logo/logodampol.jpg',
    authImage: '/landingpage/dampolzz.jpg',
    address: 'Dampol, Pulilan, Bulacan, Philippines',
    facebookUrl: 'https://www.facebook.com/D1stNHS/',
    facebookLabel: 'Facebook Page',
    copyright: '© {year} Dampol 1st National High School',
    columns: [
      {
        id: 'fcol-quick',
        title: 'Quick Links',
        links: [
          { id: 'home', label: 'Home', to: '/' },
          { id: 'about', label: 'About', to: '/about' },
          { id: 'programs', label: 'Programs', to: '/programs' },
          { id: 'contact', label: 'Contact', to: '/contact' },
        ],
      },
      {
        id: 'fcol-students',
        title: 'For Students',
        links: [
          { id: 'signin', label: 'Sign in', to: '/login' },
          { id: 'register', label: 'Register', to: '/register' },
          { id: 'news', label: 'Announcements', to: '/announcements' },
        ],
      },
      {
        id: 'fcol-partners',
        title: 'Partners',
        links: [{ id: 'deped', label: 'Department of Education', to: 'https://www.deped.gov.ph/' }],
        logos: [{ id: 'deped-logo', image: '/logo/deped.png', alt: 'Department of Education logo' }],
      },
    ],
    bottomLinks: [
      { id: 'b-contact', label: 'Contact', to: '/contact' },
      { id: 'b-about', label: 'About', to: '/about' },
    ],
  },
};

export function mergeCms(remote) {
  const landing = { ...DEFAULT_CMS.landing, ...(remote.landing || {}) };
  landing.banner = { ...DEFAULT_CMS.landing.banner, ...(landing.banner || {}) };
  if (!landing.slides?.length) landing.slides = DEFAULT_CMS.landing.slides;
  if (!landing.aboutCards?.length) landing.aboutCards = DEFAULT_CMS.landing.aboutCards;
  delete landing.bulletinCards;
  const footer = { ...DEFAULT_CMS.footer, ...(remote.footer || {}) };
  if (!footer.columns?.length) footer.columns = DEFAULT_CMS.footer.columns;
  return {
    landing,
    about: { ...DEFAULT_CMS.about, ...(remote.about || {}) },
    contact: { ...DEFAULT_CMS.contact, ...(remote.contact || {}) },
    footer,
  };
}

export function formatFooterText(value) {
  return String(value || '').replace('{year}', String(new Date().getFullYear()));
}

export function isExternalUrl(value) {
  return /^https?:\/\//i.test(String(value || '').trim());
}

export function cmsLines(value) {
  return String(value || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

export function cmsPairs(value) {
  return cmsLines(value).map((line) => {
    const index = line.indexOf('|');
    return index === -1 ? ['', line] : [line.slice(0, index).trim(), line.slice(index + 1).trim()];
  });
}
