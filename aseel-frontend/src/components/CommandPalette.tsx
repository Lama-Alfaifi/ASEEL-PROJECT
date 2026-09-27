import {
  Compass, CornerDownLeft, Languages, MapPin, Moon, Bookmark, MessageSquare, Library, Search, Sparkles, type LucideIcon,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { CITIES } from '../data/saudiMap';
import { REGIONS, TOPICS, regionName, topicName } from '../lib/regions';
import { navigate } from '../lib/router';
import { truncate } from '../lib/utils';
import { useApp } from '../state/store';
import { NAV } from './Shell';
import { clsx } from '../lib/utils';

interface Item { id: string; group: string; label: string; hint?: string; icon: LucideIcon; run: () => void }

/** Smart search: jump anywhere, or just type a question and ask it. */
export function CommandPalette() {
  const { paletteOpen, setPaletteOpen, t, lang, threads, saved, sourceIndex, send, setSettings, settings } = useApp();
  const [q, setQ] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const close = () => setPaletteOpen(false);

  useEffect(() => {
    if (paletteOpen) {
      setQ('');
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [paletteOpen]);

  const items = useMemo<Item[]>(() => {
    const go = (to: string) => () => { close(); navigate(to); };
    const list: Item[] = [];
    const query = q.trim();
    const needle = query.toLowerCase();

    if (query.length > 2) {
      list.push({
        id: 'ask', group: t('pal.ask'), label: query, hint: t('pal.askHint'), icon: Sparkles,
        run: async () => { close(); const id = await send(query); if (id) navigate(`/ask/${id}`); },
      });
    }
    NAV.forEach((n) => list.push({ id: `nav-${n.to}`, group: t('pal.go'), label: t(n.key), icon: n.icon, run: go(n.to) }));
    REGIONS.forEach((r) =>
      list.push({ id: `r-${r.id}`, group: t('pal.regions'), label: regionName(r.id, lang), hint: lang === 'ar' ? r.en : r.ar, icon: MapPin, run: go(`/explore/${r.id}`) }),
    );
    CITIES.forEach((c) =>
      list.push({ id: `c-${c.id}`, group: t('pal.cities'), label: lang === 'ar' ? c.nameAr : c.name, hint: regionName(c.region, lang), icon: MapPin, run: go(`/explore/${c.region}?city=${c.id}`) }),
    );
    TOPICS.forEach((tp) =>
      list.push({
        id: `t-${tp.id}`, group: t('pal.topics'), label: topicName(tp, lang), hint: t('pal.topicHint'), icon: tp.icon,
        run: async () => { close(); const id = await send(tp.query('general')); if (id) navigate(`/ask/${id}`); },
      }),
    );
    threads.slice(0, 8).forEach((th) => list.push({ id: `th-${th.id}`, group: t('pal.chats'), label: th.title, icon: MessageSquare, run: go(`/ask/${th.id}`) }));
    saved.slice(0, 20).forEach((s) => list.push({ id: `sv-${s.id}`, group: t('pal.saved'), label: truncate(s.title, 80), icon: Bookmark, run: go(`/saved?open=${s.id}`) }));
    sourceIndex.slice(0, 60).forEach((s) =>
      list.push({ id: `src-${s.key}`, group: t('pal.sources'), label: truncate(s.source.question, 80), hint: s.source.category, icon: Library, run: go(`/sources?q=${encodeURIComponent(s.source.question.slice(0, 60))}`) }),
    );
    list.push({ id: 'theme', group: t('pal.actions'), label: t('settings.theme'), icon: Moon, run: () => { setSettings({ theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark' }); close(); } });
    list.push({ id: 'lang', group: t('pal.actions'), label: settings.lang === 'ar' ? 'English' : 'العربية', icon: Languages, run: () => { setSettings({ lang: settings.lang === 'ar' ? 'en' : 'ar' }); close(); } });
    list.push({ id: 'explore', group: t('pal.actions'), label: t('nav.explore'), icon: Compass, run: go('/explore') });

    if (!needle) return list.filter((i) => i.group === t('pal.go') || i.group === t('pal.regions') || i.group === t('pal.chats') || i.group === t('pal.topics')).slice(0, 14);
    const scored = list
      .filter((i) => i.id !== 'ask')
      .map((i) => {
        const hay = `${i.label} ${i.hint ?? ''}`.toLowerCase();
        const pos = hay.indexOf(needle);
        return { i, score: pos === -1 ? -1 : pos === 0 ? 2 : 1 };
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((x) => x.i)
      .slice(0, 9);
    const askItem = list.filter((i) => i.id === 'ask');
    const looksLikeQuestion = /\s/.test(query) || query.endsWith('?') || query.length > 14;
    return looksLikeQuestion ? [...askItem, ...scored] : [...scored, ...askItem];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, lang, threads, saved, sourceIndex, settings.lang, t]);

  useEffect(() => setActive(0), [q]);
  useEffect(() => {
    listRef.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  if (!paletteOpen) return null;

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(items.length - 1, a + 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); items[active]?.run(); }
    else if (e.key === 'Escape') close();
  };

  let lastGroup = '';
  return (
    <div className="palette-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="palette" role="dialog" aria-modal="true" aria-label={t('search.open')} onKeyDown={onKey}>
        <div className="palette-input">
          <Search size={19} aria-hidden="true" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t('pal.placeholder')}
            aria-label={t('pal.placeholder')}
            aria-controls="palette-list"
            dir="auto"
          />
          <kbd>Esc</kbd>
        </div>
        <div className="palette-list" id="palette-list" role="listbox" ref={listRef}>
          {items.length === 0 && <p className="muted palette-empty">{t('pal.none')}</p>}
          {items.map((it, i) => {
            const header = it.group !== lastGroup ? it.group : null;
            lastGroup = it.group;
            const Icon = it.icon;
            return (
              <div key={it.id}>
                {header && <div className="palette-group">{header}</div>}
                <button
                  role="option"
                  aria-selected={i === active}
                  data-active={i === active}
                  className={clsx('palette-item', i === active && 'is-active')}
                  onMouseMove={() => setActive(i)}
                  onClick={() => it.run()}
                >
                  <Icon size={17} aria-hidden="true" />
                  <span className="palette-label" dir="auto">{it.label}</span>
                  {it.hint && <span className="muted small">{it.hint}</span>}
                  {i === active && <CornerDownLeft size={14} className="muted" aria-hidden="true" />}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
