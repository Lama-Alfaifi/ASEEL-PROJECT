import type { Lang, SavedItem, Source } from './types';

export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

export const truncate = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);

export function timeAgo(ts: number, lang: Lang): string {
  const diff = (ts - Date.now()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(lang === 'ar' ? 'ar' : 'en', { numeric: 'auto' });
  const abs = Math.abs(diff);
  if (abs < 60) return rtf.format(0, 'second');
  if (abs < 3600) return rtf.format(Math.round(diff / 60), 'minute');
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), 'hour');
  if (abs < 86400 * 30) return rtf.format(Math.round(diff / 86400), 'day');
  return new Intl.DateTimeFormat(lang === 'ar' ? 'ar' : 'en', { dateStyle: 'medium' }).format(ts);
}

export const pct = (v: number) => `${Math.round(v * 100)}%`;

export const sourceKey = (s: Pick<Source, 'region' | 'question'>) =>
  `${s.region.trim().toLowerCase()}::${s.question.trim().toLowerCase().replace(/\s+/g, ' ')}`;

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    return ok;
  }
}

export function download(filename: string, text: string, mime = 'text/markdown') {
  const url = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function evidenceMarkdown(sources: Source[]): string {
  if (!sources.length) return '';
  const rows = sources.map(
    (s) => `- **${s.region}${s.category ? ` / ${s.category}` : ''}** — ${s.question}\n  ${s.answer.replace(/\n+/g, ' ')}`,
  );
  return `\n\n### Evidence from the ASEEL knowledge base\n\n${rows.join('\n')}\n`;
}

export function savedToMarkdown(items: SavedItem[]): string {
  const head = `# ASEEL collection\n\nExported ${new Date().toLocaleString()}\n`;
  const body = items
    .map((i) => {
      const meta = [i.region, i.category, i.confidence != null ? `confidence ${pct(i.confidence)}` : ''].filter(Boolean).join(' · ');
      const tags = i.tags.length ? `\nTags: ${i.tags.map((t) => `#${t}`).join(' ')}` : '';
      const note = i.note ? `\n> ${i.note.replace(/\n/g, '\n> ')}` : '';
      return `\n---\n\n## ${i.title}\n\n_${meta}_${tags}\n\n${i.body}${note}${i.sources ? evidenceMarkdown(i.sources) : ''}`;
    })
    .join('\n');
  return head + body + '\n';
}

export const clsx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(' ');
