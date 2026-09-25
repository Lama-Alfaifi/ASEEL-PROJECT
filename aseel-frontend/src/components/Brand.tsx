import { useId } from 'react';

/* -------------------------------------------------------
   LOGO MARK — سيفين ونخلة بشكل هندسي واضح
-------------------------------------------------------- */
export function LogoMark({ size = 38 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      aria-hidden="true"
      className="logo-mark"
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Palm trunk */}
        <line x1="32" y1="16" x2="32" y2="34" />

        {/* Palm leaves */}
        <path d="M32 16 C26 8, 20 8, 15 13" />
        <path d="M32 16 C38 8, 44 8, 49 13" />
        <path d="M32 16 C24 13, 19 17, 17 22" />
        <path d="M32 16 C40 13, 45 17, 47 22" />

        {/* Swords */}
        <path d="M20 40 C30 34, 34 34, 44 40" />
        <path d="M20 44 C30 38, 34 38, 44 44" />
      </g>

      {/* Palm crown center */}
      <circle cx="32" cy="16" r="4" fill="var(--gold)" />
    </svg>
  );
}

/* -------------------------------------------------------
   WORDMARK — ASEEL + أصيل
-------------------------------------------------------- */
export function Wordmark() {
  return (
    <span className="wordmark">
      <span className="wordmark-latin">ASEEL</span>
      <span className="wordmark-ar" lang="ar">أصيل</span>
    </span>
  );
}

/* -------------------------------------------------------
   SADU BAND — شريط زخرفي مستوحى من السدو
-------------------------------------------------------- */
export function SaduBand({
  height = 14,
  className = '',
}: {
  height?: number;
  className?: string;
}) {
  const id = useId().replace(/:/g, '');

  return (
    <svg
      className={`sadu ${className}`}
      width="100%"
      height={height}
      aria-hidden="true"
      preserveAspectRatio="none"
    >
      <defs>
        <pattern id={id} width="28" height="14" patternUnits="userSpaceOnUse">
          <rect width="28" height="14" style={{ fill: 'var(--sadu-ground)' }} />

          <polygon
            points="14,1 22,7 14,13 6,7"
            style={{ fill: 'var(--gold)' }}
          />

          <polygon
            points="14,4.6 17.4,7 14,9.4 10.6,7"
            style={{ fill: 'var(--sadu-ground)' }}
          />

          <path
            d="M0 7 L3 4 L6 7 L3 10Z M22 7 L25 4 L28 7 L25 10Z"
            style={{ fill: 'var(--rust)' }}
          />
        </pattern>
      </defs>

      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
