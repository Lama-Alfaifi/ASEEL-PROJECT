import { Bookmark, BookmarkCheck, ChevronDown, Copy, Library } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { navigate } from '../lib/router';
import { normalizeRegion } from '../lib/regions';
import type { AnswerStatus, RegionOrGeneral, Source } from '../lib/types';
import { clsx, copyText, evidenceMarkdown, truncate } from '../lib/utils';
import { useApp } from '../state/store';
import { Markdown } from './Markdown';
import { SourceCard } from './SourceCard';
import { RegionTag, StatusPill, TrustBar } from './Trust';

interface Props {
  refKey: string;
  title?: string;
  query?: string;
  answer: string;
  status: AnswerStatus;
  confidence: number;
  sources: Source[];
  compact?: boolean;
  actions?: ReactNode;
  onAsk?: (q: string) => void;
}

/** The core unit of ASEEL: an answer, how much to trust it, and the evidence behind it. */
export function AnswerCard({ refKey, title, query, answer, status, confidence, sources, compact, actions, onAsk }: Props) {
  const { t, isSaved, toggleSave, toast } = useApp();
  const [showEvidence, setShowEvidence] = useState(false);
  const saved = isSaved(refKey);
  const grounded = status === 'grounded';

  const regions = useMemo(() => {
    const counts = new Map<RegionOrGeneral, number>();
    sources.forEach((s) => {
      const r = normalizeRegion(s.region);
      counts.set(r, (counts.get(r) ?? 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([r]) => r);
  }, [sources]);

  const edge = regions[0] ?? 'general';

  return (
    <article
      className={clsx('answer', !grounded && 'answer-fallback', compact && 'answer-compact')}
      style={{ ['--edge' as string]: `var(--r-${edge})` }}
    >
      <header className="answer-head">
        <StatusPill status={status} />
        <TrustBar value={confidence} />
      </header>

      {title && <h3 className="answer-title" dir="auto">{title}</h3>}

      {answer ? <Markdown>{answer}</Markdown> : <p className="muted">{t('answer.empty')}</p>}

      {!grounded && (
        <div className="tips">
          <strong>{t('fallback.title')}</strong>
          <ul>
            <li>{t('fallback.tip1')}</li>
            <li>{t('fallback.tip2')}</li>
            <li>{t('fallback.tip3')}</li>
          </ul>
        </div>
      )}

      {regions.length > 0 && (
        <div className="answer-regions">
          <span className="muted small">{t('answer.drawnFrom')}</span>
          {regions.map((r) => <RegionTag key={r} region={r} />)}
        </div>
      )}

      <footer className="answer-foot">
        <button
          className={clsx('btn btn-quiet', showEvidence && 'is-on')}
          onClick={() => setShowEvidence((v) => !v)}
          aria-expanded={showEvidence}
          disabled={sources.length === 0}
        >
          <Library size={16} aria-hidden="true" />
          {sources.length ? t('answer.evidence', { n: sources.length }) : t('answer.noEvidence')}
          {sources.length > 0 && <ChevronDown size={15} className={clsx('chev', showEvidence && 'up')} aria-hidden="true" />}
        </button>
        <span className="spacer" />
        {actions}
        <button
          className="icon-btn"
          aria-label={saved ? t('action.unsave') : t('action.save')}
          aria-pressed={saved}
          title={saved ? t('action.unsave') : t('action.save')}
          onClick={() =>
            toggleSave({
              refKey, kind: 'answer', title: title || truncate(query || answer, 80), body: answer,
              region: edge, query, confidence, sources,
            })
          }
        >
          {saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
        </button>
        <button
          className="icon-btn"
          aria-label={t('action.copy')}
          title={t('action.copy')}
          onClick={async () => { if (await copyText(answer + evidenceMarkdown(sources))) toast(t('toast.copied')); }}
        >
          <Copy size={17} />
        </button>
      </footer>

      {showEvidence && (
        <div className="evidence">
          <p className="muted small">{grounded ? t('answer.evidenceNote') : t('answer.evidenceNoteWeak')}</p>
          {sources.map((s, i) => (
            <SourceCard
              key={`${s.region}-${s.question}-${i}`}
              source={s}
              onAsk={onAsk ?? ((q) => { navigate(`/ask?q=${encodeURIComponent(q)}`); })}
            />
          ))}
        </div>
      )}
    </article>
  );
}
