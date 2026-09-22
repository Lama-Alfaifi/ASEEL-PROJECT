import { useId } from 'react';

/** Two interlocked squares (an eight-pointed star) — a common motif in Saudi geometric ornament. */
export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" className="logo-mark">
      <g transform="translate(32 32)" fill="none" stroke="currentColor" strokeWidth="3.6" strokeLinejoin="round">
        <rect x="-16" y="-16" width="32" height="32" />
        <rect x="-16" y="-16" width="32" height="32" transform="rotate(45)" />
      </g>
      <circle cx="32" cy="32" r="5.5" style={{ fill: 'var(--gold)' }} />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="wordmark">
      <span className="wordmark-latin">ASEEL</span>
      <span className="wordmark-ar" lang="ar">أصيل</span>
    </span>
  );
}

/** A woven strip inspired by Sadu textile bands. Purely decorative. */
export function SaduBand({ height = 14, className = '' }: { height?: number; className?: string }) {
  const id = useId().replace(/:/g, '');
  return (
    <svg className={`sadu ${className}`} width="100%" height={height} aria-hidden="true" preserveAspectRatio="none">
      <defs>
        <pattern id={id} width="28" height="14" patternUnits="userSpaceOnUse">
          <rect width="28" height="14" style={{ fill: 'var(--sadu-ground)' }} />
          <polygon points="14,1 22,7 14,13 6,7" style={{ fill: 'var(--gold)' }} />
          <polygon points="14,4.6 17.4,7 14,9.4 10.6,7" style={{ fill: 'var(--sadu-ground)' }} />
          <path d="M0 7 L3 4 L6 7 L3 10Z M22 7 L25 4 L28 7 L25 10Z" style={{ fill: 'var(--rust)' }} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
