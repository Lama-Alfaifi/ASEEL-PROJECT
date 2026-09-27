import { Check, Loader2, Search, ShieldCheck, Sparkles, X, Compass } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useApp } from '../state/store';
import { clsx } from '../lib/utils';

const STEPS = [
  { key: 'pipe.understand', icon: Compass, at: 0 },
  { key: 'pipe.retrieve', icon: Search, at: 3 },
  { key: 'pipe.validate', icon: ShieldCheck, at: 7.5 },
  { key: 'pipe.respond', icon: Sparkles, at: 9 },
] as const;

/**
 * The API is a single request, so real per-agent progress isn't available.
 * This walks the same four stages ASEEL runs (graph.py) on an approximate timeline
 * so people understand what the wait is for.
 */
export function PipelineLoader({ onCancel, compact = false }: { onCancel?: () => void; compact?: boolean }) {
  const { t } = useApp();
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t0 = performance.now();
    const id = window.setInterval(() => setElapsed((performance.now() - t0) / 1000), 250);
    return () => window.clearInterval(id);
  }, []);
  const stage = STEPS.reduce((acc, s, i) => (elapsed >= s.at ? i : acc), 0);

  return (
    <div className={clsx('pipeline', compact && 'pipeline-compact')} role="status" aria-live="polite">
      <ol>
        {STEPS.map((s, i) => {
          const state = i < stage ? 'done' : i === stage ? 'active' : 'todo';
          const Icon = s.icon;
          return (
            <li key={s.key} className={`step step-${state}`}>
              <span className="step-dot" aria-hidden="true">
                {state === 'done' ? <Check size={14} /> : state === 'active' ? <Loader2 size={14} className="spin" /> : <Icon size={14} />}
              </span>
              <span className="step-label">{t(s.key)}</span>
            </li>
          );
        })}
      </ol>
      <div className="pipeline-foot">
        <span className="muted small">{t('pipe.wait', { s: Math.floor(elapsed) })}</span>
        {onCancel && (
          <button className="btn btn-quiet btn-sm" onClick={onCancel}><X size={14} aria-hidden="true" /> {t('action.cancel')}</button>
        )}
      </div>
    </div>
  );
}
