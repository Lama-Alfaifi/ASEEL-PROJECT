import { ArrowRight, Bookmark, Compass, MessageSquare, Search, ShieldCheck, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { SaduBand } from '../components/Brand';
import { SaudiMap } from '../components/SaudiMap';
import { SAMPLE_QUESTIONS, TOPICS, topicHint, topicName } from '../lib/regions';
import { navigate } from '../lib/router';
import { timeAgo, truncate } from '../lib/utils';
import { useApp } from '../state/store';

const HOW = [
  { icon: Compass, title: 'pipe.understand', desc: 'how.understand' },
  { icon: Search, title: 'pipe.retrieve', desc: 'how.retrieve' },
  { icon: ShieldCheck, title: 'pipe.validate', desc: 'how.validate' },
  { icon: Sparkles, title: 'pipe.respond', desc: 'how.respond' },
] as const;

export default function Home() {
  const { t, lang, send, threads, saved } = useApp();
  const [q, setQ] = useState('');

  const ask = async (text: string) => {
    const id = await send(text);
    if (id) navigate(`/ask/${id}`);
  };

  return (
    <div className="page home">
      <section className="hero">
        <div className="hero-copy">
          <h1>{t('home.title')}</h1>
          <p className="lead">{t('home.sub')}</p>

          <form
            className="hero-search"
            onSubmit={(e) => { e.preventDefault(); if (q.trim()) void ask(q); }}
          >
            <Search size={20} aria-hidden="true" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t('home.placeholderShort')}
              aria-label={t('home.placeholder')}
              dir="auto"
            />
            <button className="btn btn-primary" type="submit" disabled={!q.trim()}>{t('home.ask')}</button>
          </form>

          <div className="try">
            <span className="muted small">{t('home.try')}</span>
            <div className="chips">
              {SAMPLE_QUESTIONS.slice(0, 4).map((p) => (
                <button key={p} className="chip chip-btn" dir="ltr" onClick={() => void ask(p)}>{p}</button>
              ))}
            </div>
          </div>
        </div>

        <figure className="hero-map">
          <SaduBand height={14} />
          <SaudiMap onSelect={(r) => navigate(`/explore/${r}`)} />
          <figcaption className="small muted">{t('home.mapHint')}</figcaption>
        </figure>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>{t('home.topics')}</h2>
          <p className="muted">{t('home.topicsSub')}</p>
        </div>
        <div className="topic-grid">
          {TOPICS.map((tp) => {
            const Icon = tp.icon;
            return (
              <button key={tp.id} className="topic" onClick={() => void ask(tp.query('general'))}>
                <span className="topic-icon"><Icon size={22} aria-hidden="true" /></span>
                <span className="topic-text">
                  <strong>{topicName(tp, lang)}</strong>
                  <span className="muted small">{topicHint(tp, lang)}</span>
                </span>
                <ArrowRight size={17} className="flip topic-arrow" aria-hidden="true" />
              </button>
            );
          })}
        </div>
      </section>

      <section className="section how-section">
        <div className="section-head">
          <h2>{t('home.how')}</h2>
          <p className="muted">{t('home.howSub')}</p>
        </div>
        <ol className="how">
          {HOW.map((s, i) => {
            const Icon = s.icon;
            return (
              <li key={s.title}>
                <span className="how-num" aria-hidden="true"><Icon size={20} /></span>
                <h3><span className="how-i">{i + 1}.</span> {t(s.title)}</h3>
                <p className="muted">{t(s.desc)}</p>
              </li>
            );
          })}
        </ol>
      </section>

      {(threads.length > 0 || saved.length > 0) && (
        <section className="section two-col">
          <div>
            <div className="section-head"><h2>{t('home.recent')}</h2></div>
            {threads.length === 0 && <p className="muted">{t('home.noChats')}</p>}
            <ul className="mini-list">
              {threads.slice(0, 4).map((th) => (
                <li key={th.id}>
                  <a href={`#/ask/${th.id}`}>
                    <MessageSquare size={16} aria-hidden="true" />
                    <span dir="auto">{truncate(th.title, 60)}</span>
                    <span className="muted small">{timeAgo(th.updatedAt, lang)}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="section-head"><h2>{t('nav.saved')}</h2></div>
            {saved.length === 0 && <p className="muted">{t('home.noSaved')}</p>}
            <ul className="mini-list">
              {saved.slice(0, 4).map((s) => (
                <li key={s.id}>
                  <a href={`#/saved?open=${s.id}`}>
                    <Bookmark size={16} aria-hidden="true" />
                    <span dir="auto">{truncate(s.title, 60)}</span>
                    <span className="muted small">{timeAgo(s.savedAt, lang)}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}
