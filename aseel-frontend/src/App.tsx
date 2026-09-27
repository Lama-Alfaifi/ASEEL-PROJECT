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
import { useApp } from './state/store';
import Feedback from './pages/Feedback';


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
  case 'ask':
    page = <Ask key={parts[1] ?? 'new'} threadId={parts[1]} />;
    break;

  case 'explore':
    page = <Explore regionParam={parts[1]} />;
    break;

  case 'plan':
    page = <Plan />;
    break;

  case 'saved':
    page = <Saved />;
    break;

  case 'settings':
    page = <Settings />;
    break;

  case 'feedback':
    page = <Feedback />;
    break;

  default:
    page = <Home />;
}

  return (
    <div className="app">
      <style>{`
        /* ==========================================
           1. الوضع العادي (LIGHT MODE)
        ========================================== */
        body, .app, .main-col, main {
          background-color: #EFECE6 !important;
          background-image: url('/bg-pattern.jpg') !important;
          background-size: cover !important;
          background-position: center !important;
          background-repeat: no-repeat !important;
          background-attachment: fixed !important;
        }

        /* الشريط الجانبي بيج طيني دافئ */
        aside, .sidebar, [data-sidebar], .mobile-nav {
          background-color: #C8BC9E !important;
          color: #2D261E !important;
        }

        aside a, .sidebar a, aside button, .sidebar button, aside svg, .sidebar svg {
          color: #2D261E !important;
        }

        aside a:hover, .sidebar a:hover, .nav-link.is-active {
          background-color: #BBAF90 !important;
          color: #1A140E !important;
        }

        /* الكلمات والشعارات (عربي وإنجليزي) في الوضع العادي - أخضر زيتي فاخر */
        .wordmark, .brand, .brand span, .brand-text, [class*="wordmark"], [class*="brand"] {
          color: #0E3B2E !important;
          font-weight: bold !important;
        }

        /* لون العناوين - أخضر زيتي فاخر */
        h1, h2, h3, h4, h5, h6, .hero-title, main h1, main h2, main h3 {
          color: #0E3B2E !important;
        }


        /* ==========================================
           2. الوضع الداكن (DARK MODE) - أخضر زمردي ملكي
        ========================================== */
        [data-theme="dark"] body, 
        [data-theme="dark"] .app, 
        [data-theme="dark"] .main-col, 
        [data-theme="dark"] main {
          background-color: #091C15 !important;
          background-image: linear-gradient(rgba(9, 28, 21, 0.92), rgba(9, 28, 21, 0.92)), url('/bg-pattern.jpg') !important;
          color: #E2D7C3 !important;
        }

        /* الكلمات والشعارات (عربي وإنجليزي) في الوضع الداكن - أبيض ناصع بالكامل */
        [data-theme="dark"] .wordmark, 
        [data-theme="dark"] .brand, 
        [data-theme="dark"] .brand span, 
        [data-theme="dark"] .brand-text, 
        [data-theme="dark"] [class*="wordmark"], 
        [data-theme="dark"] [class*="brand"] {
          color: #FFFFFF !important;
          font-weight: bold !important;
        }

        /* الشريط الجانبي في الدارك مود */
        [data-theme="dark"] aside, 
        [data-theme="dark"] .sidebar, 
        [data-theme="dark"] [data-sidebar], 
        [data-theme="dark"] .mobile-nav {
          background-color: #05140E !important;
          color: #E2D7C3 !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
        }

        [data-theme="dark"] aside a, 
        [data-theme="dark"] .sidebar a, 
        [data-theme="dark"] aside button, 
        [data-theme="dark"] .sidebar button, 
        [data-theme="dark"] aside svg, 
        [data-theme="dark"] .sidebar svg {
          color: #D3C5AB !important;
        }

        [data-theme="dark"] .nav-link.is-active, 
        [data-theme="dark"] aside a:hover, 
        [data-theme="dark"] .sidebar a:hover {
          background-color: #0E3B2E !important;
          color: #FFFFFF !important;
        }

        /* ألوان العناوين والنصوص في الدارك مود */
        [data-theme="dark"] h1, 
        [data-theme="dark"] h2, 
        [data-theme="dark"] h3, 
        [data-theme="dark"] h4, 
        [data-theme="dark"] .hero-title, 
        [data-theme="dark"] main h1, 
        [data-theme="dark"] main h2, 
        [data-theme="dark"] main h3,
        [data-theme="dark"] p,
        [data-theme="dark"] span {
          color: #E6DFD3 !important;
        }

        [data-theme="dark"] .search-trigger, 
        [data-theme="dark"] button.chip, 
        [data-theme="dark"] .topbar {
          background-color: #0D261C !important;
          border-color: #174A3B !important;
          color: #E2D7C3 !important;
        }

        .api-pill {
          background-color: rgba(0, 0, 0, 0.05) !important;
          color: inherit !important;
          border-color: rgba(0, 0, 0, 0.1) !important;
        }
      `}</style>

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