import { useId, useState } from 'react';
import { CITIES, MAP_H, MAP_W, PROVINCES, REGION_ANCHORS, REGION_OUTLINES, type City } from '../data/saudiMap';
import { REGIONS, regionName } from '../lib/regions';
import type { RegionId, RegionOrGeneral } from '../lib/types';
import { useApp } from '../state/store';
import { clsx } from '../lib/utils';

interface Props {
  selected?: RegionOrGeneral | null;
  onSelect?: (r: RegionId) => void;
  showCities?: boolean;
  onCity?: (c: City) => void;
  activeCityId?: string | null;
  labels?: boolean;
  className?: string;
}

/** Each region is filled with its own woven motif so the map reads as a textile. */
function Patterns({ id }: { id: string }) {
  const stroke = { stroke: '#fff', strokeOpacity: 0.34, strokeWidth: 2, fill: 'none' } as const;
  const solid = { fill: '#fff', fillOpacity: 0.3 } as const;
  const tile = (rid: RegionId, children: React.ReactNode) => (
    <pattern key={rid} id={`${id}-${rid}`} width="28" height="28" patternUnits="userSpaceOnUse">
      <rect width="28" height="28" style={{ fill: `var(--r-${rid})` }} />
      {children}
    </pattern>
  );
  return (
    <defs>
      {tile('central', <>
        <path d="M14 2 L26 14 L14 26 L2 14Z" {...stroke} />
        <rect x="11" y="11" width="6" height="6" transform="rotate(45 14 14)" {...solid} />
      </>)}
      {tile('west', <path d="M0 8 L7 2 L14 8 L21 2 L28 8 M0 22 L7 16 L14 22 L21 16 L28 22" {...stroke} />)}
      {tile('east', <path d="M0 14 L7 4 L14 14Z M14 26 L21 16 L28 26Z" {...solid} />)}
      {tile('south', <>
        <path d="M14 3 L25 25 L3 25Z" {...stroke} />
        <path d="M14 12 L20 23 L8 23Z" {...solid} />
      </>)}
      {tile('north', <>
        <path d="M14 3v22M3 14h22" {...stroke} />
        <circle cx="14" cy="14" r="3" {...solid} />
      </>)}
    </defs>
  );
}

export function SaudiMap({ selected = null, onSelect, showCities = false, onCity, activeCityId, labels = true, className }: Props) {
  const { lang, t } = useApp();
  const id = useId().replace(/:/g, '');
  const [hover, setHover] = useState<RegionId | null>(null);
  const focus = (hover ?? (selected && selected !== 'general' ? selected : null)) as RegionId | null;
  const dimOthers = selected && selected !== 'general';

  return (
    <svg
      viewBox={`0 0 ${MAP_W} ${MAP_H}`}
      className={clsx('saudi-map', className)}
      role="group"
      aria-label={t('map.label')}
    >
      <Patterns id={id} />

      {REGIONS.map((r) => {
        const isSel = selected === r.id;
        const dim = dimOthers && !isSel && hover !== r.id;
        return (
          <g
            key={r.id}
            className={clsx('region', isSel && 'is-selected', dim && 'is-dim', onSelect && 'is-interactive')}
            role={onSelect ? 'button' : undefined}
            tabIndex={onSelect ? 0 : undefined}
            aria-label={regionName(r.id, lang)}
            aria-pressed={onSelect ? isSel : undefined}
            onClick={() => onSelect?.(r.id)}
            onKeyDown={(e) => {
              if (onSelect && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                onSelect(r.id);
              }
            }}
            onMouseEnter={() => setHover(r.id)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(r.id)}
            onBlur={() => setHover(null)}
          >
            {PROVINCES.filter((p) => p.region === r.id).map((p) => (
              <path key={p.id} d={p.d} className="prov" style={{ fill: `url(#${id}-${r.id})` }} />
            ))}
          </g>
        );
      })}

      {/* region silhouette on top of everything so borders stay crisp */}
      {REGIONS.map((r) => (
        <path key={r.id} d={REGION_OUTLINES[r.id]} className={clsx('outline', focus === r.id && 'is-focus')} fill="none" pointerEvents="none" />
      ))}

      {labels &&
        REGIONS.map((r) => (
          <text
            key={r.id}
            x={REGION_ANCHORS[r.id].x}
            y={REGION_ANCHORS[r.id].y}
            className={clsx('region-label', lang === 'ar' && 'is-ar', focus === r.id && 'is-focus')}
            textAnchor="middle"
            pointerEvents="none"
          >
            {regionName(r.id, lang)}
          </text>
        ))}

      {showCities &&
        CITIES.map((c) => (
          <g
            key={c.id}
            className={clsx('pin', activeCityId === c.id && 'is-active')}
            transform={`translate(${c.x} ${c.y})`}
            role="button"
            tabIndex={0}
            aria-label={lang === 'ar' ? c.nameAr : c.name}
            onClick={(e) => {
              e.stopPropagation();
              onCity?.(c);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onCity?.(c);
              }
            }}
          >
            <circle r="16" className="pin-hit" />
            <circle r="7" className="pin-dot" />
            <text x={c.id === 'jeddah' ? -13 : 13} y="6" textAnchor={c.id === 'jeddah' ? 'end' : 'start'} className="pin-label">
              {lang === 'ar' ? c.nameAr : c.name}
            </text>
          </g>
        ))}
    </svg>
  );
}
