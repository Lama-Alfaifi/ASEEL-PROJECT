import { ArrowRight, Check, Loader2, MapPin, MessageSquare, RefreshCw, Shuffle, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { AnswerCard } from '../components/AnswerCard';
import { PipelineLoader } from '../components/PipelineLoader';
import { SaudiMap } from '../components/SaudiMap';
import { ErrorNotice } from '../components/States';
import { CITIES, type City } from '../data/saudiMap';
import {
  REGIONS, REGION_IDS, TOPICS, citiesOf, provinceLabel, provincesOf, regionEnglish, regionName, topicHint, topicName, type Topic,
} from '../lib/regions';
import { navigate, useRoute } from '../lib/router';
import type { Discovery, RegionId, RegionOrGeneral } from '../lib/types';
import { clsx } from '../lib/utils';
import { useApp, type DiscoverSpec } from '../state/store';

const topicKey = (tp: Topic, r: RegionOrGeneral) => `topic:${tp.id}:${r}`;
const cityKey = (c: City) => `city:${c.id}`;

export default function Explore({ regionParam }: { regionParam?: string }) {
  const { t, lang, discover, discoveries, discoveryLoading, discoveryError, removeDiscovery } = useApp();
  const { params } = useRoute();
  const [showCities, setShowCities] = useState(true);
  const [flash, setFlash] = useState<string | null>(null);
  const cityParam = params.get('city');

  const selected: RegionOrGeneral | null =
    regionParam === 'general' ? 'general' : REGION_IDS.includes(regionParam as RegionId) ? (regionParam as RegionId) : null;

  /* ---- spec builders (the query text is always English; the UI text is localised) ---- */
  const topicSpec = (tp: Topic, r: RegionOrGeneral): DiscoverSpec => ({
    key: topicKey(tp, r), kind: 'topic', title: `${tp.en} — ${regionEnglish(r)}`, query: tp.query(r), region: r, meta: { topic: tp.id },
  });
  const citySpec = (c: City): DiscoverSpec => ({
    key: cityKey(c), kind: 'city', title: c.name,
    query: `What customs and etiquette should I know when visiting ${c.name}, Saudi Arabia?`,
    region: c.region, meta: { city: c.id },
  });
  const specFromKey = (key: string): DiscoverSpec | null => {
    const [kind, a, b] = key.split(':');
    if (kind === 'topic') {
      const tp = TOPICS.find((x) => x.id === a);
      return tp ? topicSpec(tp, b as RegionOrGeneral) : null;
    }
    if (kind === 'city') {
      const c = CITIES.find((x) => x.id === a);
      return c ? citySpec(c) : null;
    }
    return null;
  };

  const run = async (spec: DiscoverSpec, force = false) => {
    const d = await discover(spec, force);
    if (d) setFlash(d.key);
  };

  /* deep link: /explore/west?city=jeddah */
  const lastCity = useRef<string | null>(null);
  useEffect(() => {
    if (!cityParam || lastCity.current === cityParam) return;
    lastCity.current = cityParam;
    const c = CITIES.find((x) => x.id === cityParam);
    if (c) void run(citySpec(c));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityParam]);

  useEffect(() => {
    if (!flash) return;
    const el = document.getElementById(`card-${flash}`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    setFlash(null);
  }, [flash, discoveries]);

  const titleOf = (d: Discovery) => {
    if (d.kind === 'topic') {
      const tp = TOPICS.find((x) => x.id === d.meta?.topic);
      return tp ? `${topicName(tp, lang)} — ${regionName(d.region, lang)}` : d.title;
    }
    if (d.kind === 'city') {
      const c = CITIES.find((x) => x.id === d.meta?.city);
      return c ? `${lang === 'ar' ? c.nameAr : c.name} — ${regionName(d.region, lang)}` : d.title;
    }
    return d.title;
  };

  const cards = useMemo(
    () =>
      Object.values(discoveries)
        .filter((d) => d.kind !== 'brief' && d.region === selected)
        .sort((a, b) => b.at - a.at),
    [discoveries, selected],
  );
  const loadingKeys = Object.keys(discoveryLoading).filter((k) => discoveryLoading[k] && specFromKey(k)?.region === selected);
  const errorKeys = Object.keys(discoveryError).filter((k) => discoveryError[k] && specFromKey(k)?.region === selected);

  const surprise = () => {
    const pool: DiscoverSpec[] = [];
    [...REGION_IDS, 'general' as const].forEach((r) => TOPICS.forEach((tp) => { if (!discoveries[topicKey(tp, r)]) pool.push(topicSpec(tp, r)); }));
    const pick = pool[Math.floor(Math.random() * pool.length)];
    if (!pick) return;
    navigate(`/explore/${pick.region}`);
    void run(pick);
  };

  return (
    <div className="page explore">
      <div className="explore-map">
        <div className="map-card map-card-lg">
          <SaudiMap
            selected={selected}
            onSelect={(r) => navigate(`/explore/${r}`)}
            showCities={showCities}
            activeCityId={cityParam}
            onCity={(c) => navigate(`/explore/${c.region}?city=${c.id}`)}
          />
        </div>
        <div className="map-tools">
          <button className={clsx('chip chip-btn', selected === 'general' && 'is-on')} onClick={() => navigate('/explore/general')}>
            {t('explore.general')}
          </button>
          <label className="switch">
            <input type="checkbox" checked={showCities} onChange={(e) => setShowCities(e.target.checked)} />
            <span>{t('explore.cities')}</span>
          </label>
          <button className="btn btn-quiet btn-sm" onClick={surprise}><Shuffle size={15} aria-hidden="true" /> {t('explore.surprise')}</button>
        </div>
        <p className="small muted map-credit">{t('explore.credit')}</p>
      </div>

      <div className="explore-panel">
        {!selected ? (
          <div className="panel-intro">
            <h1>{t('explore.title')}</h1>
            <p className="lead">{t('explore.intro')}</p>
            <ul className="region-list">
              {REGIONS.map((r) => {
                const n = Object.values(discoveries).filter((d) => d.region === r.id && d.kind !== 'brief').length;
                return (
                  <li key={r.id}>
                    <button className="region-row" style={{ ['--edge' as string]: `var(--r-${r.id})` }} onClick={() => navigate(`/explore/${r.id}`)}>
                      <span className="swatch" aria-hidden="true" />
                      <span className="region-row-text">
                        <strong>{regionName(r.id, lang)}</strong>
                        <span className="muted small">{provincesOf(r.id).map((p) => provinceLabel(p, lang)).join(', ')}</span>
                      </span>
                      {n > 0 && <span className="count">{n}</span>}
                      <ArrowRight size={16} className="flip" aria-hidden="true" />
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : (
          <>
            <header className="region-head" style={{ ['--edge' as string]: `var(--r-${selected})` }}>
              <span className="swatch swatch-lg" aria-hidden="true" />
              <div>
                <h1>{regionName(selected, lang)}</h1>
                <p className="muted">{selected === 'general' ? t('explore.generalNote') : (lang === 'ar' ? regionEnglish(selected) : REGIONS.find((r) => r.id === selected)!.ar)}</p>
              </div>
              <button className="btn btn-sm" onClick={() => navigate(`/ask?region=${selected}`)}>
                <MessageSquare size={15} aria-hidden="true" /> {t('explore.askHere')}
              </button>
            </header>

            {selected !== 'general' && (
              <>
                <div className="chips provinces" aria-label={t('explore.provinces')}>
                  {provincesOf(selected).map((p) => <span key={p.id} className="chip chip-quiet">{provinceLabel(p, lang)}</span>)}
                </div>
                <p className="small muted">{t('explore.provincesNote')}</p>
                <div className="chips">
                  {citiesOf(selected).map((c) => (
                    <button
                      key={c.id}
                      className={clsx('chip chip-btn', cityParam === c.id && 'is-on')}
                      onClick={() => navigate(`/explore/${selected}?city=${c.id}`)}
                    >
                      <MapPin size={13} aria-hidden="true" /> {lang === 'ar' ? c.nameAr : c.name}
                      {discoveries[cityKey(c)] && <Check size={13} aria-hidden="true" />}
                    </button>
                  ))}
                </div>
              </>
            )}

            <h2 className="panel-h">{t('explore.topics')}</h2>
            <div className="topic-grid topic-grid-sm">
              {TOPICS.map((tp) => {
                const key = topicKey(tp, selected);
                const done = !!discoveries[key];
                const loading = !!discoveryLoading[key];
                const Icon = tp.icon;
                return (
                  <button key={tp.id} className={clsx('topic', done && 'is-done')} disabled={loading} onClick={() => void run(topicSpec(tp, selected))}>
                    <span className="topic-icon">{loading ? <Loader2 size={20} className="spin" /> : <Icon size={20} aria-hidden="true" />}</span>
                    <span className="topic-text">
                      <strong>{topicName(tp, lang)}</strong>
                      <span className="muted small">{topicHint(tp, lang)}</span>
                    </span>
                    {done && <Check size={16} className="topic-check" aria-label={t('explore.loaded')} />}
                  </button>
                );
              })}
            </div>

            <div className="cards">
              {loadingKeys.map((k) => (
                <div key={k} className="card-loading">
                  <p className="small muted">{t('explore.loading')}</p>
                  <PipelineLoader compact />
                </div>
              ))}
              {errorKeys.map((k) => (
                <ErrorNotice key={k} error={discoveryError[k]!} onRetry={() => { const s = specFromKey(k); if (s) void run(s, true); }} />
              ))}
              {cards.map((d) => (
                <div key={d.key} id={`card-${d.key}`}>
                  <AnswerCard
                    refKey={`d:${d.key}`}
                    title={titleOf(d)}
                    query={d.query}
                    answer={d.result.answer}
                    status={d.result.status}
                    confidence={d.result.confidence}
                    sources={d.result.sources}
                    compact
                    actions={
                      <>
                        <button className="icon-btn" aria-label={t('action.refresh')} title={t('action.refresh')} onClick={() => { const s = specFromKey(d.key); if (s) void run(s, true); }}>
                          <RefreshCw size={16} />
                        </button>
                        <button className="icon-btn" aria-label={t('action.delete')} title={t('action.delete')} onClick={() => removeDiscovery(d.key)}>
                          <Trash2 size={16} />
                        </button>
                      </>
                    }
                  />
                </div>
              ))}
              {cards.length === 0 && loadingKeys.length === 0 && errorKeys.length === 0 && (
                <p className="muted empty-hint">{t('explore.pick')}</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

