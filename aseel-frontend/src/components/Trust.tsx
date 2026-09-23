import { CircleAlert, ShieldCheck } from 'lucide-react';
import { normalizeRegion, regionName } from '../lib/regions';
import type { AnswerStatus } from '../lib/types';
import { useApp } from '../state/store';
import { pct } from '../lib/utils';

export const VALIDATION_THRESHOLD = 0.5; // graph.py / validation.py: confidence >= 0.5 passes

export type TrustLevel = 'strong' | 'fair' | 'low';
export const trustLevel = (v: number): TrustLevel => (v >= 0.75 ? 'strong' : v >= VALIDATION_THRESHOLD ? 'fair' : 'low');

/** Ten woven segments, with a tick where validation passes. */
export function TrustBar({ value }: { value: number }) {
  const { t } = useApp();
  const level = trustLevel(value);
  const filled = Math.round(value * 10);
  return (
    <div className={`trust trust-${level}`} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)} aria-label={t('trust.label')}>
      <div className="trust-segs" aria-hidden="true">
        {Array.from({ length: 10 }, (_, i) => (
          <i key={i} className={i < filled ? 'on' : ''} />
        ))}
        <b className="trust-tick" />
      </div>
      <span className="trust-text">
        <strong>{pct(value)}</strong> {t(`trust.${level}` as const)}
      </span>
    </div>
  );
}

export function StatusPill({ status }: { status: AnswerStatus }) {
  const { t } = useApp();
  return status === 'grounded' ? (
    <span className="pill pill-ok"><ShieldCheck size={14} aria-hidden="true" /> {t('status.grounded')}</span>
  ) : (
    <span className="pill pill-warn"><CircleAlert size={14} aria-hidden="true" /> {t('status.fallback')}</span>
  );
}

export function RegionTag({ region }: { region: string }) {
  const { lang } = useApp();
  const id = normalizeRegion(region);
  return (
    <span className="rtag" style={{ ['--edge' as string]: `var(--r-${id})` }}>
      <i aria-hidden="true" />
      {regionName(id, lang)}
    </span>
  );
}
