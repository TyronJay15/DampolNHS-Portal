function Icon({ d, className }) {
  return (
    <span className={`school-icon ${className || ''}`} aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <path fill="currentColor" d={d} />
      </svg>
    </span>
  );
}

export const CapIcon = () => (
  <Icon d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zm-7 12.18v3.32L12 21l7-2.5v-3.32L12 18.5 5 15.18z" />
);
export const QuoteIcon = () => (
  <Icon d="M7 6H3v6h4a4 4 0 0 1-4 4v2a6 6 0 0 0 6-6V6zm14 0h-4v6h4a4 4 0 0 1-4 4v2a6 6 0 0 0 6-6V6z" />
);
export const EyeIcon = () => (
  <Icon d="M12 5c5 0 9 4.5 10 7-1 2.5-5 7-10 7S3 14.5 2 12c1-2.5 5-7 10-7zm0 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6z" />
);
export const TargetIcon = () => (
  <Icon d="M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2zm0 6a4 4 0 1 0 4 4h-2a2 2 0 1 1-2-2V8z" />
);
export const PinIcon = () => (
  <Icon d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z" />
);
export const PhoneIcon = () => (
  <Icon d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.7 21 3 13.3 3 3c0-.6.4-1 1-1h3.4c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.4 0 .7-.2 1L6.6 10.8z" />
);
export const MailIcon = () => (
  <Icon d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5L4 8V6l8 5 8-5v2z" />
);
export const ClockIcon = () => (
  <Icon d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 11h-5V11h4V6h2v7z" />
);
export const ArrowIcon = () => (
  <Icon d="M5 11h10.17l-3.58-3.59L13 6l6 6-6 6-1.41-1.41L15.17 13H5z" />
);
export const TrophyIcon = () => (
  <Icon d="M7 3h10v2h2a2 2 0 0 1-2 3.4V10a5 5 0 0 1-4 4.9V17h3v2H8v-2h3v-2.1A5 5 0 0 1 7 10V8.4A2 2 0 0 1 5 5h2V3zm10 2h-1v1.2A1 1 0 0 0 17 5zM7 5H6a1 1 0 0 0 1 1.2V5z" />
);
export const UsersIcon = () => (
  <Icon d="M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4zM8 12a3.5 3.5 0 1 0-3.5-3.5A3.5 3.5 0 0 0 8 12zm8 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4zM8 14c-.3 0-.7 0-1 .1-2.4.5-7 1.7-7 3.9V20h6v-2c0-1.1.4-2 1.1-2.8A11 11 0 0 1 8 14z" />
);
export const BookIcon = () => (
  <Icon d="M18 2H8a3 3 0 0 0-3 3v14a3 3 0 0 0 3 3h12V4a2 2 0 0 0-2-2zm0 16H8a1 1 0 0 1 0-2h10v2z" />
);
export const HeartIcon = () => (
  <Icon d="M12 21s-7.2-4.6-9.5-8.4A5.7 5.7 0 0 1 12 6.1a5.7 5.7 0 0 1 9.5 6.5C19.2 16.4 12 21 12 21z" />
);
export const FacebookIcon = () => (
  <Icon d="M14 3h3V0h-3c-2.8 0-5 2.2-5 5v3H6v4h3v9h4v-9h3.2l.8-4H13V5c0-.6.4-1 1-1z" />
);
export const MegaphoneIcon = () => (
  <Icon d="M21 4v12l-8-2.7V17a3 3 0 0 1-3 3H9a3 3 0 0 1-2.8-4L3 15V7l18-3z" />
);
