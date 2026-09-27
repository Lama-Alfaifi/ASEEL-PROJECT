import {
  Bookmark, Command, Compass, Languages, Library, ListChecks, MessageSquare, Moon, Search, Settings2, Sun, House,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { useRoute } from '../lib/router';
import { clsx } from '../lib/utils';
import { useApp } from '../state/store';
import type { TKey } from '../lib/i18n';
import { LogoMark, SaduBand, Wordmark } from './Brand';

export const NAV: { to: string; key: TKey; icon: typeof House }[] = [
  { to: '/', key: 'nav.home', icon: House },
  { to: '/ask', key: 'nav.ask', icon: MessageSquare },
  { to: '/explore', key: 'nav.explore', icon: Compass },
  { to: '/plan', key: 'nav.plan', icon: ListChecks },
  { to: '/sources', key: 'nav.sources', icon: Library },
  { to: '/saved', key: 'nav.saved', icon: Bookmark },
  { to: '/settings', key: 'nav.settings', icon: Settings2 },
];

const isActive = (to: string, first: string | undefined) => (to === '/' ? !first : to === `/${first}`);

function ApiPill() {
  const { api, t, checkApi } = useApp();
  return (
    <button className={clsx('api-pill', `api-${api.state}`)} onClick={checkApi} title={t('api.recheck')}>
      <i aria-hidden="true" />
      {api.state === 'online' ? t('api.online') : api.state === 'offline' ? t('api.offline') : t('api.checking')}
      {api.state === 'online' && api.latency != null && <span className="muted small" dir="ltr">{api.latency} ms</span>}
    </button>
  );
}

export function Sidebar() {
  const { t, saved, threads } = useApp();
  const { parts } = useRoute();
  return (
    <aside className="sidebar">
      <a href="#/" className="brand" aria-label="ASEEL">
        <LogoMark size={34} />
        <Wordmark />
      </a>
      <nav aria-label="Main">
        {NAV.map(({ to, key, icon: Icon }) => (
          <a key={to} href={`#${to}`} className={clsx('nav-link', isActive(to, parts[0]) && 'is-active')} aria-current={isActive(to, parts[0]) ? 'page' : undefined}>
            <Icon size={19} aria-hidden="true" />
            <span>{t(key)}</span>
            {to === '/saved' && saved.length > 0 && <span className="count">{saved.length}</span>}
            {to === '/ask' && threads.length > 0 && <span className="count">{threads.length}</span>}
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">
        <ApiPill />
        <p className="small">{t('side.promise')}</p>
      </div>
      <SaduBand height={12} className="sidebar-band" />
    </aside>
  );
}

export function TopBar({ children }: { children?: ReactNode }) {
  const { t, lang, setSettings, setPaletteOpen } = useApp();
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  return (
    <header className="topbar">
      <a href="#/" className="brand brand-mobile" aria-label="ASEEL">
        <LogoMark size={28} />
        <Wordmark />
      </a>
      <button className="search-trigger" onClick={() => setPaletteOpen(true)} aria-label={t('search.open')}>
        <Search size={17} aria-hidden="true" />
        <span>{t('search.placeholder')}</span>
        <kbd><Command size={11} aria-hidden="true" />K</kbd>
      </button>
      {children}
      <div className="topbar-actions">
        <span className="hide-mobile"><ApiPill /></span>
        <button className="icon-btn" onClick={() => setSettings({ lang: lang === 'ar' ? 'en' : 'ar' })} aria-label={t('settings.language')} title={lang === 'ar' ? 'English' : 'العربية'}>
          <Languages size={19} />
          <span className="lang-code">{lang === 'ar' ? 'EN' : 'ع'}</span>
        </button>
        <button
          className="icon-btn"
          onClick={() => setSettings({ theme: dark ? 'light' : 'dark' })}
          aria-label={t('settings.theme')}
          title={t('settings.theme')}
        >
          {dark ? <Sun size={19} /> : <Moon size={19} />}
        </button>
      </div>
    </header>
  );
}

export function MobileNav() {
  const { t } = useApp();
  const { parts } = useRoute();
  const items = NAV.filter((n) => n.to !== '/settings');
  return (
    <nav className="mobile-nav" aria-label="Main">
      {items.map(({ to, key, icon: Icon }) => (
        <a key={to} href={`#${to}`} className={clsx(isActive(to, parts[0]) && 'is-active')} aria-current={isActive(to, parts[0]) ? 'page' : undefined}>
          <Icon size={21} aria-hidden="true" />
          <span>{t(key)}</span>
        </a>
      ))}
    </nav>
  );
}

export function Toasts() {
  const { toasts } = useApp();
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((x) => <div key={x.id} className="toast">{x.text}</div>)}
    </div>
  );
}
