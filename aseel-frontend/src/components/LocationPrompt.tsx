import { MapPin } from 'lucide-react';
import { useState } from 'react';
import { useApp } from '../state/store';

/**
 * One-time, non-blocking location-permission card. It is shown only while the
 * choice is still "unknown"; after Allow / Not Now (or a browser decision) it
 * never appears again, so users are not asked on every question.
 */
export function LocationPrompt() {
  const { t, location, allowLocation, dismissLocation } = useApp();
  const [busy, setBusy] = useState(false);

  if (location.permission !== 'unknown' || !('geolocation' in navigator)) return null;

  return (
    <div className="loc-prompt" role="region" aria-label={t('loc.prompt')}>
      <MapPin size={18} aria-hidden="true" />
      <p>{t('loc.prompt')}</p>
      <div className="loc-actions">
        <button
          type="button"
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            await allowLocation();
            setBusy(false);
          }}
        >
          {t('loc.allow')}
        </button>
        <button type="button" className="btn" disabled={busy} onClick={dismissLocation}>
          {t('loc.notNow')}
        </button>
      </div>
    </div>
  );
}
