import { RotateCcw, WifiOff } from 'lucide-react';
import type { ReactNode } from 'react';
import type { ApiFailure } from '../lib/types';
import { navigate } from '../lib/router';
import { useApp } from '../state/store';

export function EmptyState({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      {icon && <div className="empty-icon" aria-hidden="true">{icon}</div>}
      <h3>{title}</h3>
      {children && <p className="muted">{children}</p>}
      {action}
    </div>
  );
}

export function ErrorNotice({ error, onRetry }: { error: ApiFailure; onRetry?: () => void }) {
  const { t, settings } = useApp();
  const key = (`err.${error.kind}`) as 'err.network';
  return (
    <div className="notice notice-error" role="alert">
      <WifiOff size={20} aria-hidden="true" />
      <div>
        <strong>{t(key)}</strong>
        <p className="small">
          {error.kind === 'network'
            ? t('err.networkHelp', { base: settings.apiBase })
            : error.status ? `${error.message} (${error.status})` : error.message}
        </p>
        <div className="row gap-s">
          {onRetry && (
            <button className="btn btn-sm" onClick={onRetry}><RotateCcw size={14} aria-hidden="true" /> {t('action.retry')}</button>
          )}
          <button className="btn btn-quiet btn-sm" onClick={() => navigate('/settings')}>{t('err.openSettings')}</button>
        </div>
      </div>
    </div>
  );
}
