const CAMPUS_FALLBACK = '/landingpage/dampolzz.jpg';

function isLogo(url) {
  return /logo/i.test(String(url || ''));
}

function isCampusShot(slide) {
  const hay = [slide.title, slide.body, slide.kicker, slide.image].join(' ');
  return /campus|building|glimpse/i.test(hay) && slide.image && !isLogo(slide.image);
}

export function campusPhoto(cms) {
  const slides = cms?.landing?.slides || [];
  const campus = slides.find(isCampusShot);
  if (campus?.image) return campus.image;

  const auth = cms?.footer?.authImage;
  if (auth && !isLogo(auth)) return auth;

  const first = slides.find((slide) => slide.image && !isLogo(slide.image));
  return first?.image || CAMPUS_FALLBACK;
}
