import { Download, Loader2, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { DEFAULT_API_BASE, normalizeBase, pingApi } from '../lib/api';
import type { ThemePref } from '../lib/types';
import { clsx, download } from '../lib/utils';
import { useApp } from '../state/store';

export default function Settings() {
  const { t, settings, setSettings, api, checkApi, exportAll, clearData, threads, saved, discoveries, toast } = useApp();
  const [base, setBase] = useState(settings.apiBase);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const test = async () => {
    setTesting(true);
    setResult(null);
    const r = await pingApi(base);
    setResult(r.ok ? t('settings.testOk', { ms: r.latency, msg: r.message ?? 'OK' }) : t('settings.testFail'));
    setTesting(false);
  };

  const apply = () => {
    setSettings({ apiBase: normalizeBase(base) });
    setBase(normalizeBase(base));
    toast(t('toast.saved'));
    setTimeout(checkApi, 50);
  };

  const confirmClear = (what: 'threads' | 'saved' | 'discoveries' | 'all') => {
    if (window.confirm(t('settings.confirm'))) { clearData(what); toast(t('toast.cleared')); }
  };

  return (
    <div className="page settings">
      <header className="page-head">
        <h1>{t('nav.settings')}</h1>
      </header>

      <section className="card-section">
        <h2>{t('settings.appearance')}</h2>
        <div className="setting-row">
          <span>{t('settings.language')}</span>
          <div className="seg" role="radiogroup" aria-label={t('settings.language')}>
            <button role="radio" aria-checked={settings.lang === 'en'} className={clsx(settings.lang === 'en' && 'is-on')} onClick={() => setSettings({ lang: 'en' })}>English</button>
            <button role="radio" aria-checked={settings.lang === 'ar'} className={clsx(settings.lang === 'ar' && 'is-on')} onClick={() => setSettings({ lang: 'ar' })}>العربية</button>
          </div>
        </div>
        <div className="setting-row">
          <span>{t('settings.theme')}</span>
          <div className="seg" role="radiogroup" aria-label={t('settings.theme')}>
            {(['light', 'dark', 'system'] as ThemePref[]).map((th) => (
              <button key={th} role="radio" aria-checked={settings.theme === th} className={clsx(settings.theme === th && 'is-on')} onClick={() => setSettings({ theme: th })}>
                {t(`settings.${th}` as 'settings.light')}
              </button>
            ))}
          </div>
        </div>
        <p className="small muted">{t('settings.langNote')}</p>
      </section>

      <section className="card-section">
        <h2>{t('settings.connection')}</h2>
        <p className="muted">{t('settings.connectionHelp')}</p>
        <label className="field">
          <span className="small muted">{t('settings.apiBase')}</span>
          <input value={base} onChange={(e) => setBase(e.target.value)} dir="ltr" spellCheck={false} placeholder={DEFAULT_API_BASE} />
        </label>
        <div className="row gap-s">
          <button className="btn btn-primary" onClick={apply} disabled={normalizeBase(base) === settings.apiBase}>{t('action.apply')}</button>
          <button className="btn" onClick={test} disabled={testing}>{testing ? <Loader2 size={15} className="spin" /> : null} {t('settings.test')}</button>
          <button className="btn btn-quiet" onClick={() => { setBase(DEFAULT_API_BASE); }}>{t('settings.reset')}</button>
        </div>
        {result && <p className={clsx('small', result === t('settings.testFail') ? 'text-bad' : 'text-good')} role="status">{result}</p>}
        <p className="small muted">
          {t('settings.status')}: <strong>{api.state === 'online' ? t('api.online') : api.state === 'offline' ? t('api.offline') : t('api.checking')}</strong>
        </p>
        <details className="small">
          <summary>{t('settings.endpoints')}</summary>
          <pre dir="ltr">{`GET  ${settings.apiBase}/        → { message }
POST ${settings.apiBase}/chat     → { answer, status, confidence_score, sources[] }
     body: { message, conversation_context }`}</pre>
        </details>
      </section>

      <section className="card-section">
        <h2>{t('settings.data')}</h2>
        <p className="muted">{t('settings.dataHelp')}</p>
        <ul className="data-list">
          <li><span>{t('settings.chats', { n: threads.length })}</span><button className="btn btn-quiet btn-sm" onClick={() => confirmClear('threads')}>{t('settings.clear')}</button></li>
          <li><span>{t('settings.savedN', { n: saved.length })}</span><button className="btn btn-quiet btn-sm" onClick={() => confirmClear('saved')}>{t('settings.clear')}</button></li>
          <li><span>{t('settings.cards', { n: Object.keys(discoveries).length })}</span><button className="btn btn-quiet btn-sm" onClick={() => confirmClear('discoveries')}>{t('settings.clear')}</button></li>
        </ul>
        <div className="row gap-s">
          <button className="btn" onClick={() => download('aseel-data.json', exportAll(), 'application/json')}><Download size={15} aria-hidden="true" /> {t('settings.export')}</button>
          <button className="btn btn-quiet btn-danger" onClick={() => confirmClear('all')}><Trash2 size={15} aria-hidden="true" /> {t('settings.clearAll')}</button>
        </div>
      </section>

      <section className="card-section">
        <h2>{t('settings.about')}</h2>
        <p className="muted">{t('settings.aboutBody')}</p>
      </section>
    </div>
  );
}
