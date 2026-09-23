import { Download, Printer, Trash2, Wand2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { AnswerCard } from '../components/AnswerCard';
import { PipelineLoader } from '../components/PipelineLoader';
import { ErrorNotice } from '../components/States';
import {
  FOCUS, OCCASIONS, REGIONS, ROLES, optionName, regionName, whereClause, type Option,
} from '../lib/regions';
import type { Discovery, RegionOrGeneral } from '../lib/types';
import { clsx, download, evidenceMarkdown, timeAgo, uid } from '../lib/utils';
import { useApp } from '../state/store';

const byId = (list: Option[], id: string) => list.find((o) => o.id === id)!;

function buildQuestion(occasion: string, role: string, region: RegionOrGeneral, focus: string[], details: string) {
  const parts = [
    `I am ${byId(ROLES, role).phrase}, and the occasion is ${byId(OCCASIONS, occasion).phrase} ${whereClause(region)}.`,
    'What etiquette and customs should I follow?',
  ];
  if (focus.length) parts.push(`Please cover ${focus.map((f) => byId(FOCUS, f).phrase).join(', ')}.`);
  if (details.trim()) parts.push(`Extra context: ${details.trim()}`);
  return parts.join(' ');
}

export default function Plan() {
  const { t, lang, discover, discoveries, discoveryLoading, discoveryError, removeDiscovery } = useApp();
  const [occasion, setOccasion] = useState('home');
  const [role, setRole] = useState('guest');
  const [region, setRegion] = useState<RegionOrGeneral>('general');
  const [focus, setFocus] = useState<string[]>([]);
  const [details, setDetails] = useState('');
  const [currentKey, setCurrentKey] = useState<string | null>(null);

  const question = useMemo(() => buildQuestion(occasion, role, region, focus, details), [occasion, role, region, focus, details]);
  const briefs = useMemo(
    () => Object.values(discoveries).filter((d) => d.kind === 'brief').sort((a, b) => b.at - a.at),
    [discoveries],
  );
  const current = currentKey ? discoveries[currentKey] : undefined;
  const loading = currentKey ? !!discoveryLoading[currentKey] : false;
  const error = currentKey ? discoveryError[currentKey] : undefined;

  const titleOf = (d: Discovery) => {
    const o = OCCASIONS.find((x) => x.id === d.meta?.occasion);
    const r = ROLES.find((x) => x.id === d.meta?.role);
    return o && r ? `${optionName(o, lang)} — ${optionName(r, lang)}, ${regionName(d.region, lang)}` : d.title;
  };

  const build = async (key = `brief:${uid()}`) => {
    setCurrentKey(key);
    await discover({
      key, kind: 'brief', query: question, region,
      title: `${byId(OCCASIONS, occasion).en} — ${byId(ROLES, role).en}`,
      meta: { occasion, role, focus: focus.join(',') },
    }, true);
  };

  const toggleFocus = (id: string) => setFocus((f) => (f.includes(id) ? f.filter((x) => x !== id) : [...f, id]));

  const exportBrief = (d: Discovery) => {
    const md = `# ${titleOf(d)}\n\n_${d.query}_\n\n${d.result.answer}${evidenceMarkdown(d.result.sources)}`;
    download(`aseel-brief-${d.key.slice(6)}.md`, md);
  };

  return (
    <div className="page plan">
      <header className="page-head no-print">
        <h1>{t('plan.title')}</h1>
        <p className="lead">{t('plan.sub')}</p>
      </header>

      <div className="plan-grid">
        <form className="plan-form no-print" onSubmit={(e) => { e.preventDefault(); void build(); }}>
          <fieldset>
            <legend>{t('plan.occasion')}</legend>
            <div className="chips">
              {OCCASIONS.map((o) => (
                <button type="button" key={o.id} className={clsx('chip chip-btn', occasion === o.id && 'is-on')} aria-pressed={occasion === o.id} onClick={() => setOccasion(o.id)}>
                  {optionName(o, lang)}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>{t('plan.role')}</legend>
            <div className="chips">
              {ROLES.map((o) => (
                <button type="button" key={o.id} className={clsx('chip chip-btn', role === o.id && 'is-on')} aria-pressed={role === o.id} onClick={() => setRole(o.id)}>
                  {optionName(o, lang)}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>{t('plan.region')}</legend>
            <div className="chips">
              {[...REGIONS.map((r) => r.id), 'general' as const].map((r) => (
                <button type="button" key={r} className={clsx('chip chip-btn', region === r && 'is-on')} aria-pressed={region === r} onClick={() => setRegion(r)} style={{ ['--edge' as string]: `var(--r-${r})` }}>
                  <i className="dot" aria-hidden="true" /> {regionName(r, lang)}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>{t('plan.focus')} <span className="muted small">{t('plan.optional')}</span></legend>
            <div className="chips">
              {FOCUS.map((o) => (
                <button type="button" key={o.id} className={clsx('chip chip-btn', focus.includes(o.id) && 'is-on')} aria-pressed={focus.includes(o.id)} onClick={() => toggleFocus(o.id)}>
                  {optionName(o, lang)}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>{t('plan.details')} <span className="muted small">{t('plan.optional')}</span></legend>
            <textarea rows={2} value={details} onChange={(e) => setDetails(e.target.value)} placeholder={t('plan.detailsPh')} dir="auto" maxLength={300} />
          </fieldset>

          <div className="preview">
            <span className="muted small">{t('plan.preview')}</span>
            <p dir="ltr">{question}</p>
          </div>

          <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
            <Wand2 size={18} aria-hidden="true" /> {loading ? t('plan.building') : t('plan.build')}
          </button>
        </form>

        <div className="plan-result brief-print">
          {loading && <PipelineLoader />}
          {error && <ErrorNotice error={error} onRetry={() => currentKey && void build(currentKey)} />}
          {!loading && current && (
            <AnswerCard
              refKey={`d:${current.key}`}
              title={titleOf(current)}
              query={current.query}
              answer={current.result.answer}
              status={current.result.status}
              confidence={current.result.confidence}
              sources={current.result.sources}
              actions={
                <>
                  <button className="icon-btn no-print" onClick={() => exportBrief(current)} aria-label={t('plan.download')} title={t('plan.download')}><Download size={17} /></button>
                  <button className="icon-btn no-print" onClick={() => window.print()} aria-label={t('plan.print')} title={t('plan.print')}><Printer size={17} /></button>
                </>
              }
            />
          )}
          {!loading && !current && !error && (
            <div className="plan-placeholder no-print">
              <p className="muted">{t('plan.placeholder')}</p>
            </div>
          )}

          {briefs.length > 0 && (
            <div className="recent-briefs no-print">
              <h2 className="panel-h">{t('plan.recent')}</h2>
              <ul className="mini-list">
                {briefs.map((d) => (
                  <li key={d.key} className={clsx(d.key === currentKey && 'is-active')}>
                    <button className="mini-row" onClick={() => setCurrentKey(d.key)}>
                      <span dir="auto">{titleOf(d)}</span>
                      <span className="muted small">{timeAgo(d.at, lang)}</span>
                    </button>
                    <button className="icon-btn icon-btn-sm" aria-label={t('action.delete')} onClick={() => { removeDiscovery(d.key); if (d.key === currentKey) setCurrentKey(null); }}>
                      <Trash2 size={15} />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
