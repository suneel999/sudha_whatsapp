import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  RefreshCcw, Bell, Calendar, Bed, Pill, Filter, CheckCircle2, Clock
} from 'lucide-react';

export type StaffRequestItem = {
  kind: 'appointment' | 'enquiry' | 'pharmacy' | 'notification' | string;
  id: string;
  title: string;
  subtitle?: string;
  patient_name?: string | null;
  phone?: string | null;
  status?: string | null;
  date?: string | null;
  time?: string | null;
  notes?: string | null;
  created_at?: number;
  raw?: Record<string, unknown>;
};

type Props = {
  apiBase: string;
};

const KIND_FILTERS = [
  { id: 'all', label: 'All requests' },
  { id: 'appointment', label: 'Appointments' },
  { id: 'enquiry', label: 'IPD Enquiries' },
  { id: 'pharmacy', label: 'Pharmacy' },
  { id: 'notification', label: 'Alerts' },
];

function kindIcon(kind: string) {
  if (kind === 'appointment') return Calendar;
  if (kind === 'enquiry') return Bed;
  if (kind === 'pharmacy') return Pill;
  return Bell;
}

function formatWhen(ts?: number) {
  if (!ts) return '-';
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

export default function StaffRequests({ apiBase }: Props) {
  const [items, setItems] = useState<StaffRequestItem[]>([]);
  const [kind, setKind] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const fetchFeed = useCallback(async () => {
    try {
      setError('');
      const res = await axios.get(`${apiBase}/api/staff/requests`, {
        params: { limit: 200, kind },
      });
      setItems(res.data || []);
    } catch (e: any) {
      setError(e?.response?.data?.error || e.message || 'Failed to load requests');
    } finally {
      setLoading(false);
    }
  }, [apiBase, kind]);

  useEffect(() => {
    setLoading(true);
    fetchFeed();
    const t = setInterval(fetchFeed, 15000);
    return () => clearInterval(t);
  }, [fetchFeed]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const item of items) {
      c[item.kind] = (c[item.kind] || 0) + 1;
    }
    return c;
  }, [items]);

  const updateStatus = async (item: StaffRequestItem, status: string) => {
    setBusyId(item.id);
    try {
      if (item.kind === 'enquiry') {
        await axios.put(`${apiBase}/api/enquiries/${item.id}/status`, { status });
      } else if (item.kind === 'pharmacy') {
        await axios.put(`${apiBase}/api/pharmacy/${item.id}/status`, { status });
      } else if (item.kind === 'appointment') {
        await axios.put(`${apiBase}/api/appointments/${item.id}/status`, { status });
      } else if (item.kind === 'notification') {
        await axios.post(`${apiBase}/api/staff/notifications/${item.id}/read`);
      }
      await fetchFeed();
    } catch (e: any) {
      setError(e?.response?.data?.error || e.message || 'Update failed');
    } finally {
      setBusyId(null);
    }
  };

  const markAllRead = async () => {
    try {
      await axios.post(`${apiBase}/api/staff/notifications/read-all`);
      await fetchFeed();
    } catch (e: any) {
      setError(e?.response?.data?.error || e.message || 'Failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-slate-800">Staff Requests Inbox</h3>
          <p className="text-sm text-slate-500">All WhatsApp bookings, IPD enquiries, pharmacy uploads, and alerts</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={markAllRead}
            className="px-3 py-2 rounded-xl border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            Mark alerts read
          </button>
          <button
            onClick={() => { setLoading(true); fetchFeed(); }}
            className="px-3 py-2 rounded-xl bg-cyan-600 text-white text-sm font-medium flex items-center gap-2 hover:bg-cyan-700"
          >
            <RefreshCcw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {KIND_FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setKind(f.id)}
            className={`px-3 py-2 rounded-full text-sm font-medium border ${
              kind === f.id
                ? 'bg-cyan-600 text-white border-cyan-600'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            <span className="inline-flex items-center gap-1">
              <Filter size={14} />
              {f.label}
              {f.id !== 'all' && counts[f.id] ? ` (${counts[f.id]})` : ''}
            </span>
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {loading && items.length === 0 ? (
          <div className="p-10 text-center text-slate-500">Loading requests...</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-slate-500">No requests yet. New WhatsApp bookings will appear here.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((item) => {
              const Icon = kindIcon(item.kind);
              const busy = busyId === item.id;
              return (
                <div key={`${item.kind}-${item.id}`} className="p-4 md:p-5 hover:bg-slate-50/80 transition">
                  <div className="flex flex-col md:flex-row md:items-start gap-4 justify-between">
                    <div className="flex gap-3 min-w-0">
                      <div className="w-11 h-11 rounded-xl bg-cyan-50 text-cyan-700 flex items-center justify-center shrink-0">
                        <Icon size={20} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-slate-800">{item.title}</p>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 uppercase tracking-wide">
                            {item.kind}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 inline-flex items-center gap-1">
                            <Clock size={12} />
                            {item.status || 'open'}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600 mt-1 break-words">{item.subtitle}</p>
                        <div className="mt-2 text-sm text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
                          {item.patient_name && <span>Patient: <b className="text-slate-700">{item.patient_name}</b></span>}
                          {item.phone && <span>Phone: <b className="text-slate-700">{item.phone}</b></span>}
                          {item.date && <span>Date: <b className="text-slate-700">{item.date}</b></span>}
                          {item.time && <span>Time: <b className="text-slate-700">{item.time}</b></span>}
                          <span>Ref: <b className="text-slate-700">{item.id}</b></span>
                          <span>{formatWhen(item.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2 shrink-0">
                      {item.kind === 'enquiry' && item.status !== 'closed' && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'closed')}
                          className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
                        >
                          Mark closed
                        </button>
                      )}
                      {item.kind === 'pharmacy' && item.status !== 'done' && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'done')}
                          className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
                        >
                          Mark done
                        </button>
                      )}
                      {item.kind === 'appointment' && item.status === 'confirmed' && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'completed')}
                          className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50 inline-flex items-center gap-1"
                        >
                          <CheckCircle2 size={14} /> Complete
                        </button>
                      )}
                      {item.kind === 'notification' && item.status === 'unread' && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'read')}
                          className="px-3 py-2 rounded-lg border border-slate-200 text-slate-700 text-sm font-medium disabled:opacity-50"
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
