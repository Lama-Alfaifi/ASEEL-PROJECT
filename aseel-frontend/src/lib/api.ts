import type { ApiFailure, AnswerStatus, ChatResult, Source } from './types';

export class ApiError extends Error implements ApiFailure {
  kind: ApiFailure['kind'];
  status?: number;
  constructor(kind: ApiFailure['kind'], message: string, status?: number) {
    super(message);
    this.kind = kind;
    this.status = status;
  }
}

export const DEFAULT_API_BASE: string = import.meta.env.VITE_API_BASE || '/api';

export const normalizeBase = (base: string) => (base.trim() || DEFAULT_API_BASE).replace(/\/+$/, '');

const str = (v: unknown): string => (typeof v === 'string' ? v : v == null ? '' : String(v));
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

function normalizeSource(raw: unknown): Source {
  const r = (raw ?? {}) as Record<string, unknown>;
  return {
    region: str(r.region) || 'General',
    category: str(r.category),
    domain: str(r.domain),
    question: str(r.question),
    answer: str(r.answer),
    relevance: num(r.relevance),
    distance: num(r.distance),
  };
}

/** Coerce the backend's ChatResponse into a predictable shape. */
export function normalizeResult(data: unknown): ChatResult {
  const d = (data ?? {}) as Record<string, unknown>;
  const status: AnswerStatus = d.status === 'grounded' ? 'grounded' : 'fallback';
  const rawConfidence = num(d.confidence_score) ?? 0;
  return {
    answer: str(d.answer),
    status,
    confidence: Math.min(1, Math.max(0, rawConfidence)),
    sources: Array.isArray(d.sources) ? d.sources.map(normalizeSource) : [],
  };
}

interface AskOptions {
  baseUrl: string;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/** POST {base}/chat  { message, conversation_context } */
export async function askAseel(message: string, context: string, opts: AskOptions): Promise<ChatResult> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, opts.timeoutMs ?? 120_000);
  const onAbort = () => controller.abort();
  opts.signal?.addEventListener('abort', onAbort);

  try {
    const res = await fetch(`${normalizeBase(opts.baseUrl)}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ message, conversation_context: context }),
      signal: controller.signal,
    });

    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = typeof body?.detail === 'string' ? body.detail : Array.isArray(body?.detail) ? 'Invalid request' : '';
      } catch {
        /* not JSON */
      }
      throw new ApiError('http', detail || `Server responded with ${res.status}`, res.status);
    }

    let json: unknown;
    try {
      json = await res.json();
    } catch {
      throw new ApiError('parse', 'The server returned an unreadable response.');
    }
    return normalizeResult(json);
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if ((e as Error)?.name === 'AbortError') {
      throw timedOut ? new ApiError('timeout', 'The request took too long.') : new ApiError('aborted', 'Cancelled.');
    }
    throw new ApiError('network', 'Could not reach the ASEEL API.');
  } finally {
    window.clearTimeout(timer);
    opts.signal?.removeEventListener('abort', onAbort);
  }
}

export interface PingResult {
  ok: boolean;
  latency: number;
  message?: string;
}

/** GET {base}/  → { message: "ASEEL API is running" } */
export async function pingApi(baseUrl: string): Promise<PingResult> {
  const t0 = performance.now();
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 6000);
  try {
    const res = await fetch(`${normalizeBase(baseUrl)}/`, { signal: controller.signal, headers: { Accept: 'application/json' } });
    const latency = Math.round(performance.now() - t0);
    if (!res.ok) return { ok: false, latency };
    const body = await res.json().catch(() => ({}));
    return { ok: true, latency, message: typeof body?.message === 'string' ? body.message : undefined };
  } catch {
    return { ok: false, latency: Math.round(performance.now() - t0) };
  } finally {
    window.clearTimeout(timer);
  }
}
