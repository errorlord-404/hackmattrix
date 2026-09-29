import { useState } from 'react';
import { Bell, Check } from 'lucide-react';
import { useFarmData } from '../../context/FarmDataContext.jsx';

export default function AlertMenu({ mobile = false }) {
  const [open, setOpen] = useState(false); const { alerts, acknowledgeAlert } = useFarmData();
  return <div className="relative">
    <button onClick={() => setOpen((value) => !value)} aria-label="Notifications" className="relative rounded-lg p-1 hover:bg-surface-muted"><Bell size={mobile ? 20 : 19} />{alerts.length > 0 && <span className="absolute -right-1 -top-1 grid size-4 place-items-center rounded-full bg-danger text-[9px] font-bold text-white">{Math.min(alerts.length, 9)}</span>}</button>
    {open && <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-border bg-white p-2 text-left shadow-xl"><p className="px-2 py-2 text-xs font-bold uppercase tracking-wide text-text-muted">Farm alerts</p>{alerts.length === 0 ? <p className="px-2 pb-3 text-sm text-text-secondary">No open alerts.</p> : alerts.map((alert) => <div className="mb-1 rounded-lg bg-amber-50 p-3" key={alert.id}><p className="text-xs font-bold text-amber-900">{alert.title}</p><p className="mt-1 text-xs leading-5 text-amber-800">{alert.message}</p><button onClick={() => acknowledgeAlert(alert.id)} className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-primary"><Check size={12} /> Mark read</button></div>)}</div>}
  </div>;
}

