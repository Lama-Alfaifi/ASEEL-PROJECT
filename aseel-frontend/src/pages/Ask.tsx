import { ArrowUp, MessageSquare, Plus, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { AnswerCard } from '../components/AnswerCard';
import { LocationPrompt } from '../components/LocationPrompt';
import { PipelineLoader } from '../components/PipelineLoader';
import { EmptyState, ErrorNotice } from '../components/States';
import { RegionTag } from '../components/Trust';
import { REGIONS, SAMPLE_QUESTIONS, TOPICS, normalizeRegion, regionName, topicName } from '../lib/regions';
import { navigate, useRoute } from '../lib/router';
import type { Message, RegionOrGeneral, Thread } from '../lib/types';
import { clsx, timeAgo, truncate } from '../lib/utils';
import { useApp } from '../state/store';

/** Region most represented in an answer's evidence (ignores "General"). */
function dominantRegion(m: Message): RegionOrGeneral | null {
  const counts = new Map<RegionOrGeneral, number>();
  m.result?.sources.forEach((s) => {
    const r = normalizeRegion(s.region);
    if (r !== 'general') counts.set(r, (counts.get(r) ?? 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
}

function hash(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export default function Ask({ threadId }: { threadId?: string }) {
  const { t, lang, threads, pending, send, retry, cancel, deleteThread, location: userLoc } = useApp();
  const { params } = useRoute();
  const thread: Thread | undefined = threads.find((x) => x.id === threadId);
  const busy = threadId ? pending[threadId] != null : false;

  const [draft, setDraft] = useState('');
  const [region, setRegion] = useState<RegionOrGeneral | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  /* /ask?q=…&region=… prefills the composer (used by "Ask about this" on sources and the Explore map) */
  const qParam = params.get('q');
  const regionParam = params.get('region');
  useEffect(() => {
    if (qParam) setDraft(qParam);
    if (regionParam) setRegion(normalizeRegion(regionParam));
    if (qParam || regionParam) taRef.current?.focus();
  }, [qParam, regionParam]);

  /* keep the newest message in view */
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [thread?.messages.length, busy]);

  /* grow the textarea with its content */
  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [draft]);

  const submit = async (text = draft, opts?: { region?: RegionOrGeneral | null }) => {
    const value = text.trim();
    if (!value || busy) return;
    const id = await send(value, { threadId: thread?.id, region: opts && 'region' in opts ? opts.region : region });
    setDraft('');
    if (id && id !== thread?.id) navigate(`/ask/${id}`);
  };

  const lastAssistant = useMemo(
    () => [...(thread?.messages ?? [])].reverse().find((m) => m.role === 'assistant' && m.result),
    [thread],
  );

  /* "Ask next": three topics tailored to the region of the last answer */
  const followUps = useMemo(() => {
    if (!lastAssistant?.result || lastAssistant.result.status !== 'grounded') return [];
    const r = dominantRegion(lastAssistant) ?? 'general';
    const start = hash(lastAssistant.id) % TOPICS.length;
    return [0, 3, 6].map((o) => TOPICS[(start + o) % TOPICS.length]).map((tp) => ({ tp, r }));
  }, [lastAssistant]);

  return (
    <div className="page ask">
      <aside className="threads" aria-label={t('ask.history')}>
        <button className="btn btn-block" onClick={() => { setDraft(''); navigate('/ask'); }}>
          <Plus size={17} aria-hidden="true" /> {t('ask.new')}
        </button>
        <ul>
          {threads.map((th) => (
            <li key={th.id} className={clsx(th.id === threadId && 'is-active')}>
              <a href={`#/ask/${th.id}`}>
                <span className="thread-title" dir="auto">{truncate(th.title, 48)}</span>
                <span className="muted small">{timeAgo(th.updatedAt, lang)}</span>
              </a>
              <button
                className="icon-btn icon-btn-sm"
                aria-label={t('action.delete')}
                onClick={() => { deleteThread(th.id); if (th.id === threadId) navigate('/ask'); }}
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
          {threads.length === 0 && <li className="muted small threads-empty">{t('ask.noHistory')}</li>}
        </ul>
      </aside>

      <section className="chat">
        <LocationPrompt />
        <div className="chat-scroll">
          {!thread ? (
            <div className="chat-empty">
              <EmptyState title={t('ask.emptyTitle')}>{t('ask.emptyBody')}</EmptyState>
              <div className="prompt-grid">
                {SAMPLE_QUESTIONS.map((p) => (
                  <button key={p} className="prompt" dir="ltr" onClick={() => void submit(p, { region: null })}>{p}</button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {thread.messages.map((m) =>
                m.role === 'user' ? (
                  <div key={m.id} className="msg msg-user">
                    <div className="bubble" dir="auto">{m.content}</div>
                    {m.regionHint && m.regionHint !== 'general' && <RegionTag region={m.regionHint} />}
                  </div>
                ) : m.error ? (
                  <div key={m.id} className="msg">
                    <ErrorNotice error={m.error} onRetry={() => retry(thread.id, m.id)} />
                  </div>
                ) : (
                  <div key={m.id} className="msg msg-assistant">
                    <AnswerCard
                      refKey={`a:${m.id}`}
                      query={m.query}
                      answer={m.content}
                      status={m.result?.status ?? 'fallback'}
                      confidence={m.result?.confidence ?? 0}
                      sources={m.result?.sources ?? []}
                      onAsk={(q) => { setDraft(q); taRef.current?.focus(); }}
                    />
                  </div>
                ),
              )}
              {busy && (
                <div className="msg msg-assistant">
                  <PipelineLoader onCancel={() => thread && cancel(thread.id)} />
                </div>
              )}
              {!busy && followUps.length > 0 && thread.messages[thread.messages.length - 1]?.role === 'assistant' && (
                <div className="followups">
                  <span className="muted small">{t('ask.next')}</span>
                  <div className="chips">
                    {followUps.map(({ tp, r }) => {
                      const Icon = tp.icon;
                      return (
                        <button key={tp.id} className="chip chip-btn" onClick={() => void submit(tp.query(r), { region: null })}>
                          <Icon size={14} aria-hidden="true" />
                          {topicName(tp, lang)}
                          {r !== 'general' && <span className="muted">· {regionName(r, lang)}</span>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              <div ref={endRef} className="chat-end" />
            </div>
          )}
        </div>

        <form className="composer" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <div className="region-pick" role="radiogroup" aria-label={t('ask.regionHint')}>
            <span className="muted small">{t('ask.region')}</span>
            {[null, ...REGIONS.map((r) => r.id), 'general' as const].map((r) => (
              <button
                key={r ?? 'auto'}
                type="button"
                role="radio"
                aria-checked={region === r}
                className={clsx('chip chip-btn', region === r && 'is-on')}
                onClick={() => setRegion(r)}
              >
                {r === null ? t('ask.auto') : regionName(r, lang)}
              </button>
            ))}
            {(userLoc.city || userLoc.region) && (
              <span className="muted small loc-chip">
                📍 {[userLoc.city?.replace(/\s+City$/i, ''), userLoc.region ? regionName(userLoc.region, lang) : null]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            )}
          </div>
          <div className="composer-box">
            <MessageSquare size={18} aria-hidden="true" className="composer-icon" />
            <textarea
              ref={taRef}
              rows={1}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  void submit();
                }
              }}
              placeholder={t('home.placeholder')}
              aria-label={t('home.placeholder')}
              dir="auto"
            />
            <button className="send" type="submit" disabled={!draft.trim() || busy} aria-label={t('action.send')}>
              <ArrowUp size={19} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
