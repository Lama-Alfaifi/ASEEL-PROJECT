import { useEffect, useState } from 'react';

/** Tiny hash router: works on any static host, no server rewrites needed. */
export function useRoute() {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const on = () => setHash(window.location.hash);
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  const raw = hash.replace(/^#/, '') || '/';
  const [pathname, query = ''] = raw.split('?');
  const parts = pathname.split('/').filter(Boolean);
  return { pathname, parts, params: new URLSearchParams(query) };
}

export function navigate(to: string) {
  window.location.hash = to;
}
