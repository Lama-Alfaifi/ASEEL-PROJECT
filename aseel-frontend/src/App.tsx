import { useEffect, useLayoutEffect } from 'react';
import { CommandPalette } from './components/CommandPalette';
import { MobileNav, Sidebar, Toasts, TopBar } from './components/Shell';
import { useRoute } from './lib/router';
import Ask from './pages/Ask';
import Explore from './pages/Explore';
import Home from './pages/Home';
import Plan from './pages/Plan';
import Saved from './pages/Saved';
import Settings from './pages/Settings';
import Sources from './pages/Sources';
import { useApp } from './state/store';

export default function App() {
  const { parts, pathname } = useRoute();
  const { setPaletteOpen, paletteOpen, t } = useApp();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen(!paletteOpen);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [paletteOpen, setPaletteOpen]);

  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  let page;
  switch (parts[0]) {
    case 'ask': page = <Ask key={parts[1] ?? 'new'} threadId={parts[1]} />; break;
    case 'explore': page = <Explore regionParam={parts[1]} />; break;
    case 'plan': page = <Plan />; break;
    case 'sources': page = <Sources />; break;
    case 'saved': page = <Saved />; break;
    case 'settings': page = <Settings />; break;
    default: page = <Home />;
  }

  return (
    <div className="app">
      <a className="skip-link" href="#main">{t('a11y.skip')}</a>
      <Sidebar />
      <div className="main-col">
        <TopBar />
        <main id="main" tabIndex={-1}>{page}</main>
      </div>
      <MobileNav />
      <CommandPalette />
      <Toasts />
    </div>
  );
}
