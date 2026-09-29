import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError } from '../api/client.js';
import { farmStateApi } from '../api/farmStateApi.js';

const FarmDataContext = createContext(null);

export function FarmDataProvider({ children }) {
  const [profile, setProfile] = useState(null); const [fields, setFields] = useState([]); const [mapFields, setMapFields] = useState([]); const [alerts, setAlerts] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(null);
  const knownAlertIds = useRef(null);
  const refresh = useCallback(async ({ background = false } = {}) => {
    if (!background) { setLoading(true); setError(null); }
    const results = await Promise.allSettled([farmStateApi.getProfile(), farmStateApi.listFields(), farmStateApi.listMapFields()]);
    const [profileResult, fieldsResult, mapResult] = results;
    if (profileResult.status === 'fulfilled') setProfile(profileResult.value); else if (!(profileResult.reason instanceof ApiError && profileResult.reason.status === 404)) setError(profileResult.reason);
    if (fieldsResult.status === 'fulfilled') setFields(fieldsResult.value); else setError(fieldsResult.reason);
    if (mapResult.status === 'fulfilled') setMapFields(mapResult.value);
    // Fetching forecast alerts also writes new, de-duplicated in-app alerts on
    // the backend. This runs immediately and every 15 minutes while Electron is open.
    if (fieldsResult.status === 'fulfilled') await Promise.allSettled(fieldsResult.value.map((field) => farmStateApi.getWeatherAlerts(field.id)));
    const alertsResult = await farmStateApi.listAlerts('open').then((value) => ({ status: 'fulfilled', value }), (reason) => ({ status: 'rejected', reason }));
    if (alertsResult.status === 'fulfilled') {
      const nextAlerts = alertsResult.value;
      setAlerts(nextAlerts);
      const priorAlertIds = knownAlertIds.current;
      knownAlertIds.current = new Set(nextAlerts.map((alert) => alert.id));
      // A failed profile read must not override the farmer's notification
      // choice. Native notifications are opt-in for the current refresh.
      const notificationsEnabled = profileResult.status === 'fulfilled' && profileResult.value.notification_preferences?.enabled !== false;
      const newAlerts = priorAlertIds ? nextAlerts.filter((alert) => !priorAlertIds.has(alert.id)) : [];
      if (notificationsEnabled && newAlerts.length && window.kisanHarness?.notifications?.showAlert) {
        void Promise.allSettled(newAlerts.slice(0, 3).map((alert) => window.kisanHarness.notifications.showAlert({
          title: alert.title || 'KisanSathi farm alert',
          message: alert.message || 'Open KisanSathi to review this farm alert.',
        })));
      }
    }
    if (!background) setLoading(false);
  }, []);
  // The initial load synchronizes this provider with the backend API.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const intervalId = window.setInterval(() => { refresh({ background: true }); }, 15 * 60 * 1000);
    return () => window.clearInterval(intervalId);
  }, [refresh]);
  const value = useMemo(() => ({ profile, fields, mapFields, alerts, loading, error, refresh, refreshFields: refresh, refreshAlerts: refresh,
    saveProfile: async (body) => { const saved = await farmStateApi.updateProfile(body); setProfile(saved); return saved; },
    createField: async (body) => { const created = await farmStateApi.createField(body); await refresh(); return created; },
    updateField: async (id, body) => { const updated = await farmStateApi.updateField(id, body); await refresh(); return updated; },
    acknowledgeAlert: async (id, status = 'read') => { await farmStateApi.updateAlert(id, status); await refresh(); },
  }), [profile, fields, mapFields, alerts, loading, error, refresh]);
  return <FarmDataContext.Provider value={value}>{children}</FarmDataContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFarmData() { const value = useContext(FarmDataContext); if (!value) throw new Error('useFarmData must be used inside FarmDataProvider'); return value; }
