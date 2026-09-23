import { Library, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { SourceCard } from '../components/SourceCard';
import { EmptyState } from '../components/States';
import { REGIONS, regionName } from '../lib/regions';
import { navigate, useRoute } from '../lib/router';
import type { RegionOrGeneral } from '../lib/types';
import { clsx } from '../lib/utils';
import { useApp } from '../state/store';

type Sort = 'relevance' | 'recent' | 'seen';

export default function Sources() {
  const { t, lang, sourceIndex, threads, discoveries } = useApp();
  const { params } = useRoute();
  const [text, setText] = useState(params.get('q') ?? '');
  const [region, setRegion] = useState<RegionOrGeneral | 'all'>('all');
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState<Sort>('relevance');

  const categories = useMemo(
    () => [...new Set(sourceIndex.map((s) => s.source.category).filter(Boolean))].sort(),
    [sourceIndex],
  );

  const regionCounts = useMemo(() => {
    const m = new Map<RegionOrGeneral, number>();
    sourceIndex.forEach((s) => m.set(s.region, (m.get(s.region) ?? 0) + 1));
    return m;
  }, [sourceIndex]);

  const answersChecked =
    threads.reduce((n, th) => n + th.messages.filter((m) => m.result).length, 0) + Object.keys(discoveries).length;

  const list = useMemo(() => {
    const needle = text.trim().toLowerCase();
    return sourceIndex
      .filter((s) => region === 'all' || s.region === region)
      .filter((s) => category === 'all' || s.source.category === category)
      .filter((s) => !needle || `${s.source.question} ${s.source.answer} ${s.source.category}`.toLowerCase().includes(needle))
      .sort((a, b) =>
        sort === 'relevance' ? (b.source.relevance ?? 0) - (a.source.relevance ?? 0)
        : sort === 'recent' ? b.lastSeen - a.lastSeen
        : b.count - a.count,
      );
  }, [sourceIndex, text, region, category, sort]);

  const total = sourceIndex.length;
  const allRegions: RegionOrGeneral[] = [...REGIONS.map((r) => r.id), 'general'];

  return (
    <div className="page sources">
      <header className="page-head">
        <h1>{t('sources.title')}</h1>
        <p className="lead">{t('sources.sub')}</p>
      </header>

      {total === 0 ? (
        <EmptyState
          icon={<Library size={26} />}
          title={t('sources.emptyTitle')}
          action={
            <div className="row gap-s center">
              <button className="btn btn-primary" onClick={() => navigate('/ask')}>{t('nav.ask')}</button>
              <button className="btn" onClick={() => navigate('/explore')}>{t('nav.explore')}</button>
            </div>
          }
        >
          {t('sources.emptyBody')}
        </EmptyState>
      ) : (
        <>
          <section className="stats" aria-label={t('sources.coverage')}>
            <div className="stat"><strong>{total}</strong><span className="muted small">{t('sources.entries')}</span></div>
            <div className="stat"><strong>{answersChecked}</strong><span className="muted small">{t('sources.answers')}</span></div>
            <div className="stat"><strong>{categories.length}</strong><span className="muted small">{t('sources.categories')}</span></div>
            <div className="coverage">
              <span className="muted small">{t('sources.coverage')}</span>
              <div className="coverage-bar" role="img" aria-label={allRegions.map((r) => `${regionName(r, lang)} ${regionCounts.get(r) ?? 0}`).join(', ')}>
                {allRegions.filter((r) => regionCounts.get(r)).map((r) => (
                  <i key={r} style={{ flexGrow: regionCounts.get(r), background: `var(--r-${r})` }} title={`${regionName(r, lang)}: ${regionCounts.get(r)}`} />
                ))}
              </div>
            </div>
          </section>

          <div className="filters">
            <label className="field-search">
              <Search size={17} aria-hidden="true" />
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t('sources.search')} aria-label={t('sources.search')} dir="auto" />
            </label>
            <label className="select">
              <span className="sr-only">{t('sources.sort')}</span>
              <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                <option value="relevance">{t('sources.byRelevance')}</option>
                <option value="recent">{t('sources.byRecent')}</option>
                <option value="seen">{t('sources.byUsed')}</option>
              </select>
            </label>
            {categories.length > 0 && (
              <label className="select">
                <span className="sr-only">{t('sources.category')}</span>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="all">{t('sources.allCategories')}</option>
                  {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
            )}
          </div>

          <div className="chips">
            <button className={clsx('chip chip-btn', region === 'all' && 'is-on')} onClick={() => setRegion('all')}>{t('sources.all')} <span className="muted">{total}</span></button>
            {allRegions.filter((r) => regionCounts.get(r)).map((r) => (
              <button key={r} className={clsx('chip chip-btn', region === r && 'is-on')} onClick={() => setRegion(r)} style={{ ['--edge' as string]: `var(--r-${r})` }}>
                <i className="dot" aria-hidden="true" /> {regionName(r, lang)} <span className="muted">{regionCounts.get(r)}</span>
              </button>
            ))}
          </div>

          <p className="small muted">{t('sources.showing', { n: list.length })}</p>
          <div className="source-grid">
            {list.map((s) => (
              <SourceCard key={s.key} source={s.source} seen={s.count} onAsk={(q) => navigate(`/ask?q=${encodeURIComponent(q)}`)} />
            ))}
          </div>
          {list.length === 0 && <p className="muted">{t('sources.noMatch')}</p>}
          <p className="small muted note-foot">{t('sources.note')}</p>
        </>
      )}
    </div>
  );
}
