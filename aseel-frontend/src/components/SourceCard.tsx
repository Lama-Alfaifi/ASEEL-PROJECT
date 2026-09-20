import { Bookmark, BookmarkCheck, Copy, MessageSquarePlus } from 'lucide-react';
import { useState } from 'react';
import { normalizeRegion } from '../lib/regions';
import type { Source } from '../lib/types';
import { copyText, pct, sourceKey } from '../lib/utils';
import { useApp } from '../state/store';
import { RegionTag } from './Trust';

interface Props {
  source: Source;
  seen?: number;
  onAsk?: (question: string) => void;
  defaultOpen?: boolean;
}

export function SourceCard({ source, seen, onAsk, defaultOpen = false }: Props) {
  const { t, isSaved, toggleSave, toast } = useApp();
  const [open, setOpen] = useState(defaultOpen);
  const region = normalizeRegion(source.region);
  const refKey = `s:${sourceKey(source)}`;
  const saved = isSaved(refKey);
  const long = source.answer.length > 220;

  return (
    <article className="source" style={{ ['--edge' as string]: `var(--r-${region})` }}>
      <header className="source-head">
        <RegionTag region={source.region} />
        {source.category && <span className="chip">{source.category}</span>}
        {source.domain && source.domain !== source.category && <span className="chip chip-quiet">{source.domain}</span>}
        {source.relevance != null && (
          <span className="rel" title={t('source.relevance')}>
            <span className="rel-bar"><i style={{ width: pct(Math.max(0, Math.min(1, source.relevance))) }} /></span>
            {pct(source.relevance)}
          </span>
        )}
      </header>
      <h4 dir="auto">{source.question || t('source.untitled')}</h4>
      <p className={open ? '' : 'clamp'} dir="auto">{source.answer}</p>
      <footer className="source-foot">
        {long && (
          <button className="link-btn" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
            {open ? t('source.less') : t('source.more')}
          </button>
        )}
        {seen != null && seen > 1 && <span className="muted small">{t('source.seen', { n: seen })}</span>}
        <span className="spacer" />
        <button
          className="icon-btn"
          aria-label={saved ? t('action.unsave') : t('action.save')}
          aria-pressed={saved}
          onClick={() =>
            toggleSave({
              refKey, kind: 'source', title: source.question || t('source.untitled'), body: source.answer,
              region, category: source.category,
            })
          }
        >
          {saved ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}
        </button>
        <button
          className="icon-btn"
          aria-label={t('action.copy')}
          onClick={async () => { if (await copyText(`${source.question}\n\n${source.answer}`)) toast(t('toast.copied')); }}
        >
          <Copy size={16} />
        </button>
        {onAsk && source.question && (
          <button className="icon-btn" aria-label={t('source.ask')} title={t('source.ask')} onClick={() => onAsk(source.question)}>
            <MessageSquarePlus size={17} />
          </button>
        )}
      </footer>
    </article>
  );
}
