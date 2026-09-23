import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode,
} from 'react';
import { ApiError, DEFAULT_API_BASE, askAseel, locateUser, pingApi } from '../lib/api';
import { normalizeRegion, regionEnglish } from '../lib/regions';
import { translate, type TKey } from '../lib/i18n';
import type {
  ApiFailure, ChatResult, DetectedLocation, Discovery, DiscoveryKind, IndexedSource, Lang, Message, RegionOrGeneral,
  SavedItem, Settings, Source, Thread,
} from '../lib/types';
import { sourceKey, truncate, uid } from '../lib/utils';

/* ---------------- persistence ---------------- */

const LS = (k: string) => `aseel.v1.${k}`;

function usePersisted<T>(key: string, initial: T, merge = false) {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(LS(key));
      if (!raw) return initial;
      const parsed = JSON.parse(raw) as T;
      return merge ? ({ ...initial, ...parsed } as T) : parsed;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(LS(key), JSON.stringify(value));
    } catch {
      /* storage full or unavailable: keep working in memory */
    }
  }, [key, value]);
  return [value, setValue] as const;
}

const DEFAULT_SETTINGS: Settings = {
  lang: navigator.language?.toLowerCase().startsWith('ar') ? 'ar' : 'en',
  theme: 'system',
  apiBase: DEFAULT_API_BASE,
};

const MAX_THREADS = 30;
const MAX_DISCOVERIES = 80;

/** Only city + region are ever persisted. Coordinates live for one function call. */
const INITIAL_LOCATION: DetectedLocation = { permission: 'unknown', city: null, region: null, detectedAt: null };

/* ---------------- helpers ---------------- */

/** Mirrors app.py: the last five earlier messages as "role: content" lines. */
function buildContext(prior: Message[]): string {
  return prior
    .filter((m) => !m.error && m.content)
    .slice(-5)
    .map((m) => `${m.role}: ${truncate(m.content, 900)}`)
    .join('\n');
}

export function describeFailure(e: unknown): ApiFailure {
  if (e instanceof ApiError) return { kind: e.kind, message: e.message, status: e.status };
  return { kind: 'network', message: (e as Error)?.message || 'Unknown error' };
}

const sentFor = (text: string, region: RegionOrGeneral | null) =>
  region && region !== 'general' ? `${text} (in the ${regionEnglish(region)} region of Saudi Arabia)` : text;

/* ---------------- context ---------------- */

export interface DiscoverSpec {
  key: string;
  kind: DiscoveryKind;
  title: string;
  query: string;
  region: RegionOrGeneral;
  meta?: Record<string, string>;
}

export type ApiState = { state: 'checking' | 'online' | 'offline'; latency?: number };

interface Ctx {
  settings: Settings;
  setSettings: (patch: Partial<Settings>) => void;
  lang: Lang;
  t: (key: TKey, vars?: Record<string, string | number>) => string;

  threads: Thread[];
  send: (text: string, opts?: { threadId?: string; region?: RegionOrGeneral | null }) => Promise<string | null>;
  retry: (threadId: string, errorMessageId: string) => void;
  cancel: (threadId: string) => void;
  deleteThread: (id: string) => void;
  pending: Record<string, number>;

  discoveries: Record<string, Discovery>;
  discover: (spec: DiscoverSpec, force?: boolean) => Promise<Discovery | null>;
  discoveryLoading: Record<string, boolean>;
  discoveryError: Record<string, ApiFailure | undefined>;
  removeDiscovery: (key: string) => void;

  saved: SavedItem[];
  isSaved: (refKey: string) => boolean;
  toggleSave: (item: Omit<SavedItem, 'id' | 'savedAt' | 'note' | 'tags'>) => void;
  updateSaved: (id: string, patch: Partial<Pick<SavedItem, 'note' | 'tags'>>) => void;
  removeSaved: (id: string) => void;

  sourceIndex: IndexedSource[];

  api: ApiState;
  checkApi: () => Promise<void>;

  location: DetectedLocation;
  allowLocation: () => Promise<void>;
  dismissLocation: () => void;
  forgetLocation: () => void;

  toast: (text: string) => void;
  toasts: { id: string; text: string }[];

  paletteOpen: boolean;
  setPaletteOpen: (v: boolean) => void;

  exportAll: () => string;
  clearData: (what: 'threads' | 'saved' | 'discoveries' | 'all') => void;
}

const AppCtx = createContext<Ctx>(null as unknown as Ctx);
export const useApp = () => useContext(AppCtx);

export function AppProvider({ children }: { children: ReactNode }) {
  const [settings, setSettingsState] = usePersisted<Settings>('settings', DEFAULT_SETTINGS, true);
  const [threads, setThreads] = usePersisted<Thread[]>('threads', []);
  const [saved, setSaved] = usePersisted<SavedItem[]>('saved', []);
  const [discoveries, setDiscoveries] = usePersisted<Record<string, Discovery>>('discoveries', {});
  const [pending, setPending] = useState<Record<string, number>>({});
  const [discoveryLoading, setDiscoveryLoading] = useState<Record<string, boolean>>({});
  const [discoveryError, setDiscoveryError] = useState<Record<string, ApiFailure | undefined>>({});
  const [api, setApi] = useState<ApiState>({ state: 'checking' });
  const [toasts, setToasts] = useState<{ id: string; text: string }[]>([]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [location, setLocation] = usePersisted<DetectedLocation>('location', INITIAL_LOCATION, true);
  /* threadId -> backend session id, so follow-ups keep server-side memory (city/region/topic). */
  const [sessions, setSessions] = usePersisted<Record<string, string>>('sessions', {});

  const lang = settings.lang;
  const t = useCallback(
    (key: TKey, vars?: Record<string, string | number>) => translate(lang, key, vars),
    [lang],
  );

  const setSettings = useCallback(
    (patch: Partial<Settings>) => setSettingsState((s) => ({ ...s, ...patch })),
    [setSettingsState],
  );

  /* apply language + theme to <html> */
  useEffect(() => {
    const el = document.documentElement;
    el.lang = lang;
    el.dir = lang === 'ar' ? 'rtl' : 'ltr';
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      const theme = settings.theme === 'system' ? (mq.matches ? 'dark' : 'light') : settings.theme;
      el.setAttribute('data-theme', theme);
    };
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, [lang, settings.theme]);

  /* refs so async callbacks always see current data */
  const threadsRef = useRef(threads);
  threadsRef.current = threads;
  const discRef = useRef(discoveries);
  discRef.current = discoveries;
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const locationRef = useRef(location);
  locationRef.current = location;
  const sessionsRef = useRef(sessions);
  sessionsRef.current = sessions;
  const controllers = useRef<Record<string, AbortController>>({});

  /* ---- toasts ---- */
  const toast = useCallback((text: string) => {
    const id = uid();
    setToasts((x) => [...x.slice(-2), { id, text }]);
    window.setTimeout(() => setToasts((x) => x.filter((i) => i.id !== id)), 2600);
  }, []);

  /* ---- API health ---- */
  const checkApi = useCallback(async () => {
    setApi((a) => ({ ...a, state: a.state === 'online' ? 'online' : 'checking' }));
    const r = await pingApi(settingsRef.current.apiBase);
    setApi({ state: r.ok ? 'online' : 'offline', latency: r.latency });
  }, []);

  useEffect(() => {
    checkApi();
    const id = window.setInterval(checkApi, 30_000);
    return () => window.clearInterval(id);
  }, [checkApi, settings.apiBase]);

  /* ---- location ---- */
  const detectLocation = useCallback(
    () =>
      new Promise<void>((resolve) => {
        if (!('geolocation' in navigator)) {
          setLocation((l) => ({ ...l, permission: 'dismissed' }));
          resolve();
          return;
        }
        navigator.geolocation.getCurrentPosition(
          async (pos) => {
            try {
              // Coordinates are used only for this call; only city/region are kept.
              const r = await locateUser(pos.coords.latitude, pos.coords.longitude, settingsRef.current.apiBase);
              const region = r.region ? normalizeRegion(r.region) : null;
              setLocation({
                permission: 'granted',
                city: r.city,
                region: region && region !== 'general' ? region : null,
                detectedAt: Date.now(),
              });
            } catch {
              // Allowed, but the API could not resolve it right now: keep whatever we had.
              setLocation((l) => ({ ...l, permission: 'granted' }));
            }
            resolve();
          },
          (err) => {
            if (err.code === err.PERMISSION_DENIED) setLocation({ ...INITIAL_LOCATION, permission: 'denied' });
            else setLocation((l) => ({ ...l, permission: 'granted' }));
            resolve();
          },
          { enableHighAccuracy: false, timeout: 20_000, maximumAge: 10 * 60_000 },
        );
      }),
    [setLocation],
  );

  const allowLocation = useCallback(() => detectLocation(), [detectLocation]);
  const dismissLocation = useCallback(() => setLocation((l) => ({ ...l, permission: 'dismissed' })), [setLocation]);
  const forgetLocation = useCallback(() => setLocation({ ...INITIAL_LOCATION, permission: 'dismissed' }), [setLocation]);

  /* silently refresh once per visit if the user already allowed it (never triggers a new browser prompt) */
  useEffect(() => {
    if (locationRef.current.permission !== 'granted' || !('geolocation' in navigator)) return;
    let cancelled = false;
    (async () => {
      try {
        const st = await navigator.permissions?.query({ name: 'geolocation' as PermissionName });
        if (st?.state === 'denied') {
          setLocation({ ...INITIAL_LOCATION, permission: 'denied' });
          return;
        }
        if (st?.state === 'prompt') return;
      } catch {
        /* Permissions API unavailable: fall through */
      }
      if (!cancelled) void detectLocation();
    })();
    return () => {
      cancelled = true;
    };
  }, [detectLocation, setLocation]);

  /* ---- chat ---- */
  const updateThread = useCallback(
    (id: string, fn: (t: Thread) => Thread) =>
      setThreads((all) => all.map((th) => (th.id === id ? fn(th) : th))),
    [setThreads],
  );

  const runAsk = useCallback(
    async (threadId: string, userMsg: Message, prior: Message[]) => {
      const ctrl = new AbortController();
      controllers.current[threadId] = ctrl;
      setPending((p) => ({ ...p, [threadId]: Date.now() }));
      try {
        /* Detected location is the last-resort fallback: only sent when the user left the region on "Auto".
           An explicit region (or "General") is already part of the message text and must win. */
        const loc = locationRef.current;
        const userLocation =
          userMsg.regionHint == null && (loc.city || loc.region)
            ? { city: loc.city, region: loc.region ? regionEnglish(loc.region) : null }
            : null;
        const res = await askAseel(userMsg.sent ?? userMsg.content, buildContext(prior), {
          baseUrl: settingsRef.current.apiBase,
          signal: ctrl.signal,
          userLocation,
          region: userMsg.regionHint,
          sessionId: sessionsRef.current[threadId] ?? null,
        });
        if (res.sessionId && sessionsRef.current[threadId] !== res.sessionId) {
          const sid = res.sessionId;
          setSessions((m) => ({ ...m, [threadId]: sid }));
        }
        const reply: Message = {
          id: uid(),
          role: 'assistant',
          content: res.answer,
          createdAt: Date.now(),
          query: userMsg.content,
          result: { status: res.status, confidence: res.confidence, sources: res.sources },
        };
        updateThread(threadId, (th) => ({ ...th, updatedAt: Date.now(), messages: [...th.messages, reply] }));
        setApi((a) => ({ ...a, state: 'online' }));
      } catch (e) {
        const failure = describeFailure(e);
        if (failure.kind !== 'aborted') {
          const reply: Message = {
            id: uid(), role: 'assistant', content: '', createdAt: Date.now(), query: userMsg.content, error: failure,
          };
          updateThread(threadId, (th) => ({ ...th, updatedAt: Date.now(), messages: [...th.messages, reply] }));
          if (failure.kind === 'network') setApi((a) => ({ ...a, state: 'offline' }));
        }
      } finally {
        delete controllers.current[threadId];
        setPending((p) => {
          const { [threadId]: _drop, ...rest } = p;
          return rest;
        });
      }
    },
    [updateThread, setSessions],
  );

  const send: Ctx['send'] = useCallback(
    async (text, opts = {}) => {
      const clean = text.trim();
      if (!clean) return null;
      const threadId = opts.threadId ?? uid();
      const region = opts.region ?? null;
      const userMsg: Message = {
        id: uid(), role: 'user', content: clean, createdAt: Date.now(), regionHint: region, sent: sentFor(clean, region),
      };
      const existing = threadsRef.current.find((th) => th.id === threadId);
      const prior = existing?.messages ?? [];
      if (existing) {
        updateThread(threadId, (th) => ({ ...th, updatedAt: Date.now(), messages: [...th.messages, userMsg] }));
      } else {
        const th: Thread = {
          id: threadId, title: truncate(clean, 56), createdAt: Date.now(), updatedAt: Date.now(), messages: [userMsg],
        };
        setThreads((all) => [th, ...all].slice(0, MAX_THREADS));
      }
      void runAsk(threadId, userMsg, prior);
      return threadId;
    },
    [runAsk, setThreads, updateThread],
  );

  const retry = useCallback(
    (threadId: string, errorId: string) => {
      const th = threadsRef.current.find((x) => x.id === threadId);
      if (!th) return;
      const idx = th.messages.findIndex((m) => m.id === errorId);
      if (idx < 1) return;
      const userMsg = th.messages[idx - 1];
      if (userMsg.role !== 'user') return;
      updateThread(threadId, (x) => ({ ...x, messages: x.messages.filter((m) => m.id !== errorId) }));
      void runAsk(threadId, userMsg, th.messages.slice(0, idx - 1));
    },
    [runAsk, updateThread],
  );

  const cancel = useCallback((threadId: string) => controllers.current[threadId]?.abort(), []);

  const deleteThread = useCallback(
    (id: string) => {
      controllers.current[id]?.abort();
      setThreads((all) => all.filter((th) => th.id !== id));
      setSessions((m) => {
        const { [id]: _drop, ...rest } = m;
        return rest;
      });
    },
    [setThreads, setSessions],
  );

  /* ---- discoveries (map topics, cities, briefs) ---- */
  const discover: Ctx['discover'] = useCallback(
    async (spec, force = false) => {
      const cached = discRef.current[spec.key];
      if (cached && !force) return cached;
      setDiscoveryLoading((m) => ({ ...m, [spec.key]: true }));
      setDiscoveryError((m) => ({ ...m, [spec.key]: undefined }));
      try {
        const res: ChatResult = await askAseel(spec.query, '', { baseUrl: settingsRef.current.apiBase });
        const d: Discovery = { ...spec, result: res, at: Date.now() };
        setDiscoveries((all) => {
          const next = { ...all, [spec.key]: d };
          const keys = Object.keys(next);
          if (keys.length > MAX_DISCOVERIES) {
            keys.sort((a, b) => next[a].at - next[b].at).slice(0, keys.length - MAX_DISCOVERIES).forEach((k) => delete next[k]);
          }
          return next;
        });
        setApi((a) => ({ ...a, state: 'online' }));
        return d;
      } catch (e) {
        const failure = describeFailure(e);
        setDiscoveryError((m) => ({ ...m, [spec.key]: failure }));
        if (failure.kind === 'network') setApi((a) => ({ ...a, state: 'offline' }));
        return null;
      } finally {
        setDiscoveryLoading((m) => ({ ...m, [spec.key]: false }));
      }
    },
    [setDiscoveries],
  );

  const removeDiscovery = useCallback(
    (key: string) =>
      setDiscoveries((all) => {
        const { [key]: _drop, ...rest } = all;
        return rest;
      }),
    [setDiscoveries],
  );

  /* ---- saved ---- */
  const isSaved = useCallback((refKey: string) => saved.some((s) => s.refKey === refKey), [saved]);

  const toggleSave: Ctx['toggleSave'] = useCallback(
    (item) => {
      const exists = saved.some((s) => s.refKey === item.refKey);
      if (exists) {
        setSaved((all) => all.filter((s) => s.refKey !== item.refKey));
        toast(translate(settingsRef.current.lang, 'toast.removed'));
      } else {
        setSaved((all) => [{ ...item, id: uid(), savedAt: Date.now(), note: '', tags: [] }, ...all]);
        toast(translate(settingsRef.current.lang, 'toast.saved'));
      }
    },
    [saved, setSaved, toast],
  );

  const updateSaved: Ctx['updateSaved'] = useCallback(
    (id, patch) => setSaved((all) => all.map((s) => (s.id === id ? { ...s, ...patch } : s))),
    [setSaved],
  );
  const removeSaved = useCallback((id: string) => setSaved((all) => all.filter((s) => s.id !== id)), [setSaved]);

  /* ---- source index: every knowledge-base entry seen so far ---- */
  const sourceIndex = useMemo<IndexedSource[]>(() => {
    const map = new Map<string, IndexedSource>();
    const add = (s: Source, query: string, at: number) => {
      if (!s.question && !s.answer) return;
      const key = sourceKey(s);
      const cur = map.get(key);
      if (cur) {
        cur.count += 1;
        cur.lastSeen = Math.max(cur.lastSeen, at);
        if (query && !cur.queries.includes(query) && cur.queries.length < 5) cur.queries.push(query);
        if ((s.relevance ?? 0) > (cur.source.relevance ?? 0)) cur.source = s;
      } else {
        map.set(key, { key, source: s, region: normalizeRegion(s.region), count: 1, lastSeen: at, queries: query ? [query] : [] });
      }
    };
    threads.forEach((th) =>
      th.messages.forEach((m) => m.result?.sources.forEach((s) => add(s, m.query ?? '', m.createdAt))),
    );
    Object.values(discoveries).forEach((d) => d.result.sources.forEach((s) => add(s, d.query, d.at)));
    return [...map.values()];
  }, [threads, discoveries]);

  /* ---- data management ---- */
  const exportAll = useCallback(
    () => JSON.stringify({ exportedAt: new Date().toISOString(), settings, threads, saved, discoveries }, null, 2),
    [settings, threads, saved, discoveries],
  );

  const clearData: Ctx['clearData'] = useCallback(
    (what) => {
      if (what === 'threads' || what === 'all') {
        Object.values(controllers.current).forEach((c) => c.abort());
        setThreads([]);
        setSessions({});
      }
      if (what === 'saved' || what === 'all') setSaved([]);
      if (what === 'discoveries' || what === 'all') setDiscoveries({});
      if (what === 'all') setLocation(INITIAL_LOCATION);
    },
    [setDiscoveries, setLocation, setSaved, setSessions, setThreads],
  );

  const value: Ctx = {
    settings, setSettings, lang, t,
    threads, send, retry, cancel, deleteThread, pending,
    discoveries, discover, discoveryLoading, discoveryError, removeDiscovery,
    saved, isSaved, toggleSave, updateSaved, removeSaved,
    location, allowLocation, dismissLocation, forgetLocation,
    sourceIndex, api, checkApi, toast, toasts, paletteOpen, setPaletteOpen, exportAll, clearData,
  };
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}
