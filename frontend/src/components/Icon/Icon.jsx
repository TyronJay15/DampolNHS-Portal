const ICONS = {
  user: 'M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4 0-7 2-7 4.5V20h14v-1.5C19 16 16 14 12 14Z',
  grades: 'M5 4h14v16H5z M8 8h8 M8 12h8 M8 16h5',
  bell: 'M6 17h12l-1.2-2.1V10a4.8 4.8 0 0 0-9.6 0v4.9Zm3.2 0a2.8 2.8 0 0 0 5.6 0',
  year: 'M7 4v2M17 4v2M5 8h14M6 6h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z',
  termplan: 'M4 5h16v14H4z M4 10h16 M9.3 5v14 M14.7 5v14',
  access: 'M8 15a4 4 0 1 1 3.9-5H21v3h-2v3h-3v-3h-4.1A4 4 0 0 1 8 15z M8 11h.01',
  sections: 'M4 6h7v5H4z M13 6h7v5h-7z M4 13h7v5H4z M13 13h7v5h-7z',
  place: 'M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11zm0-8.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z',
  assign: 'M8 7a4 4 0 1 0 0-1 M16 11a3 3 0 1 0 0-1 M3 19c.4-3 2.6-5 5-5s4.6 2 5 5 M13 19c.3-2.2 1.7-3.8 3.5-4.4',
  approve: 'M5 12.5 9.5 17 19 7',
  corrections: 'M4 15.5 14.5 5l4 4L8 19.5H4z',
  archive: 'M4 7h16l-1.2 12H5.2z M9 11h6 M3 7h18V4H3z',
  classes: 'M4 6h16v12H4z M8 6v12 M4 10h16',
  advisory: 'M7 18V6h10l-2 4 2 4H7',
  forecast: 'M4 18V6 M4 18h16 M7 14l3-3 3 2 4-5',
  guidance: 'M3 9.5 12 5l9 4.5-9 4.5z M7 11.6V15c0 1.5 2.2 3 5 3s5-1.5 5-3v-3.4 M21 9.5V14',
  audit: 'M8 6h11 M8 12h11 M8 18h11 M5 6h.01 M5 12h.01 M5 18h.01',
  history: 'M12 7v5l3 2 M12 4a8 8 0 1 0 8 8',
  cms: 'M5 6h14v4H5z M5 12h6v6H5z M13 12h6v6h-6z',
  sun: 'M12 6V3 M12 21v-3 M6 12H3 M21 12h-3 M6.4 6.4 4.3 4.3 M19.7 19.7 17.6 17.6 M6.4 17.6 4.3 19.7 M19.7 4.3 17.6 6.4 M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
  moon: 'M16.5 13A7 7 0 0 1 11 4.5 7 7 0 1 0 16.5 13z',
  account: 'M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm-7 8c.5-3.2 3.2-5 7-5s6.5 1.8 7 5',
  staff: 'M8 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM3 19c.5-3 2.8-4.5 5-4.5S12.5 16 13 19 M14 19c.3-2 1.6-3.2 3.2-3.5',
  phone: 'M7 3h3l1.2 3-2 1.4a12 12 0 0 0 7.4 7.4l1.4-2 3 1.2v3a2 2 0 0 1-2.2 2A16 16 0 0 1 5 5.2 2 2 0 0 1 7 3z',
  home: 'M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z',
  mail: 'M4 7h16v10H4z M4 7l8 6 8-6',
  search: 'M11 19a8 8 0 1 1 0-16 8 8 0 0 1 0 16z M20 20l-3.5-3.5',
  check: 'M5 12.5 9.5 17 19 7',
  pencil: 'M4 16.5 14.8 5.7l3.5 3.5L7.5 20H4z M13.2 7.3l3.5 3.5',
  alert: 'M12 4 3 19h18z M12 10v4 M12 16.8v.01',
  trash: 'M5 7h14 M9 7V4h6v3 M7 7l1 13h8l1-13 M10 11v5 M14 11v5',
  logout: 'M10 4H5v16h5 M14 8l4 4-4 4 M18 12H9',
  close: 'M6 6l12 12 M18 6 6 18',
  sliders: 'M4 7h9 M17 7h3 M15 5v4 M4 17h3 M11 17h9 M9 15v4',
  guardian: 'M8 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M16.2 11a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8z M3 19c.4-2.8 2.5-4.4 5-4.4S12.6 16.2 13 19 M14.2 19c.3-1.8 1.5-3.1 3.2-3.4',
};

export default function Icon({ name, size = 18 }) {
  const path = ICONS[name];
  if (!path) return null;
  return (
    <svg className="desk-icon" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
