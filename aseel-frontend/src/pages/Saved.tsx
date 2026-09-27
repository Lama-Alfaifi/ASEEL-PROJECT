import { Bookmark, Copy, Download, Library, MessageSquare, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Markdown } from '../components/Markdown';
import { SourceCard } from '../components/SourceCard';
import { EmptyState } from '../components/States';
import { RegionTag, TrustBar } from '../components/Trust';
import { REGIONS, regionName } from '../lib/regions';
import { navigate, useRoute } from '../lib/router';
import type { RegionOrGeneral, SavedItem } from '../lib/types';
import { clsx, copyText, download, evidenceMarkdown, savedToMarkdown, timeAgo } from '../lib/utils';
import { useApp } from '../state/store';

function SavedCard({ item, open, onToggle }: { item: SavedItem; open: boolean; onToggle: () => void }) {
  const { t, lang, updateSaved, removeSaved, toast } = useApp();
  const ref = useRef<HTMLElement>(null);
  const [tagText, setTagText] = useState('');

  useEffect(() => {
    if (open) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [open]);

  const addTags = () => {
    const tags = tagText.split(/[,\s]+/).map((x) => x.replace(/^#/, '').trim()).filter(Boolean);
    if (tags.length) updateSaved(item.id, { tags: [...new Set([...item.tags, ...tags])] });
    setTagText('');
  };

  return (
    <article ref={ref} className={clsx('saved-card', open && 'is-open')} style={{ ['--edge' as string]: `var(--r-${item.region ?? 'general'})` }}>
      <header>
        <span className="kind">{item.kind === 'answer' ? <MessageSquare size={15} aria-hidden="true" /> : <Library size={15} aria-hidden="true" />}{t(item.kind === 'answer' ? 'saved.answer' : 'saved.source')}</span>
        {item.region && <RegionTag region={item.region} />}
        {item.category && <span className="chip chip-quiet">{item.category}</span>}
        <span className="muted small spacer">{timeAgo(item.savedAt, lang)}</span>
      </header>
      <button className="saved-title" onClick={onToggle} aria-expanded={open} dir="auto">{item.title}</button>

      {open ? (
        <div className="saved-body">
          {item.kind === 'answer' ? <Markdown>{item.body}</Markdown> : <p dir="auto">{item.body}</p>}
          {item.confidence != null && <TrustBar value={item.confidence} />}
          {item.sources && item.sources.length > 0 && (
            <details className="saved-evidence">
              <summary>{t('answer.evidence', { n: item.sources.length })}</summary>
              {item.sources.map((s, i) => <SourceCard key={i} source={s} />)}
            </details>
          )}
          <label className="note">
            <span className="small muted">{t('saved.note')}</span>
            <textarea rows={2} value={item.note} onChange={(e) => updateSaved(item.id, { note: e.target.value })} placeholder={t('saved.notePh')} dir="auto" />
          </label>
          <div className="tag-row">
            {item.tags.map((tg) => (
              <button key={tg} className="chip chip-btn" onClick={() => updateSaved(item.id, { tags: item.tags.filter((x) => x !== tg) })} aria-label={`${t('action.delete')} #${tg}`}>#{tg} ×</button>
            ))}
            <input
              className="tag-input"
              value={tagText}
              onChange={(e) => setTagText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTags(); } }}
              onBlur={addTags}
              placeholder={t('saved.tagPh')}
              aria-label={t('saved.tagPh')}
            />
          </div>
          <div className="row gap-s">
            <button className="btn btn-sm" onClick={async () => { if (await copyText(`${item.title}\n\n${item.body}${item.sources ? evidenceMarkdown(item.sources) : ''}`)) toast(t('toast.copied')); }}>
              <Copy size={14} aria-hidden="true" /> {t('action.copy')}
            </button>
            <button className="btn btn-sm" onClick={() => download(`aseel-${item.id}.md`, savedToMarkdown([item]))}>
              <Download size={14} aria-hidden="true" /> {t('saved.download')}
            </button>
            {item.query && item.kind === 'answer' && (
              <button className="btn btn-quiet btn-sm" onClick={() => navigate(`/ask?q=${encodeURIComponent(item.query!)}`)}>{t('saved.askAgain')}</button>
            )}
            <span className="spacer" />
            <button className="btn btn-quiet btn-sm btn-danger" onClick={() => removeSaved(item.id)}><Trash2 size={14} aria-hidden="true" /> {t('action.delete')}</button>
          </div>
        </div>
      ) : (
        <p className="saved-preview muted" dir="auto">{item.body.replace(/[#*_>`]/g, '').slice(0, 180)}{item.body.length > 180 ? '…' : ''}</p>
      )}
      {!open && item.tags.length > 0 && <div className="tag-row">{item.tags.map((tg) => <span key={tg} className="chip chip-quiet">#{tg}</span>)}</div>}
    </article>
  );
}

export default function Saved() {
  const { t, lang, saved } = useApp();
  const { params } = useRoute();
  const [kind, setKind] = useState<'all' | 'answer' | 'source'>('all');
  const [region, setRegion] = useState<RegionOrGeneral | 'all'>('all');
  const [text, setText] = useState('');
  const [openId, setOpenId] = useState<string | null>(params.get('open'));

  useEffect(() => { const o = params.get('open'); if (o) setOpenId(o); }, [params]);

  const list = useMemo(() => {
    const needle = text.trim().toLowerCase().replace(/^#/, '');
    return saved
      .filter((s) => kind === 'all' || s.kind === kind)
      .filter((s) => region === 'all' || s.region === region)
      .filter((s) => !needle || `${s.title} ${s.body} ${s.note} ${s.tags.join(' ')}`.toLowerCase().includes(needle));
  }, [saved, kind, region, text]);

  return (
    <div className="page saved">
      <header className="page-head page-head-split">
        <div>
          <h1>{t('saved.title')}</h1>
          <p className="lead">{t('saved.sub')}</p>
        </div>
        {saved.length > 0 && (
          <button className="btn" onClick={() => download('aseel-collection.md', savedToMarkdown(list))}>
            <Download size={16} aria-hidden="true" /> {t('saved.export')}
          </button>
        )}
      </header>

      {saved.length === 0 ? (
        <EmptyState icon={<Bookmark size={26} />} title={t('saved.emptyTitle')} action={<button className="btn btn-primary" onClick={() => navigate('/explore')}>{t('nav.explore')}</button>}>
          {t('saved.emptyBody')}
        </EmptyState>
      ) : (
        <>
          <div className="filters">
            <input className="field-plain" value={text} onChange={(e) => setText(e.target.value)} placeholder={t('saved.search')} aria-label={t('saved.search')} dir="auto" />
            <div className="seg" role="radiogroup" aria-label={t('saved.type')}>
              {(['all', 'answer', 'source'] as const).map((k) => (
                <button key={k} role="radio" aria-checked={kind === k} className={clsx(kind === k && 'is-on')} onClick={() => setKind(k)}>
                  {t(k === 'all' ? 'sources.all' : k === 'answer' ? 'saved.answers' : 'saved.sources')}
                </button>
              ))}
            </div>
          </div>
          <div className="chips">
            <button className={clsx('chip chip-btn', region === 'all' && 'is-on')} onClick={() => setRegion('all')}>{t('sources.all')}</button>
            {[...REGIONS.map((r) => r.id), 'general' as const].filter((r) => saved.some((s) => s.region === r)).map((r) => (
              <button key={r} className={clsx('chip chip-btn', region === r && 'is-on')} onClick={() => setRegion(r)} style={{ ['--edge' as string]: `var(--r-${r})` }}>
                <i className="dot" aria-hidden="true" /> {regionName(r, lang)}
              </button>
            ))}
          </div>
          <div className="saved-list">
            {list.map((s) => <SavedCard key={s.id} item={s} open={openId === s.id} onToggle={() => setOpenId(openId === s.id ? null : s.id)} />)}
            {list.length === 0 && <p className="muted">{t('sources.noMatch')}</p>}
          </div>
        </>
      )}
    </div>
  );
}
