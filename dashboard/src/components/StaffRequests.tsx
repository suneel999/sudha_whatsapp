import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  RefreshCcw, Bell, Bed, Pill, TestTube, Stethoscope, ScanLine,
  CheckCircle2, Clock, Phone, MessageCircle, Search, AlertCircle
} from 'lucide-react';

export type StaffRequestItem = {
  kind: 'appointment' | 'enquiry' | 'pharmacy' | 'notification' | string;
  flow?: 'opd' | 'ultrasound' | 'lab' | 'pharmacy' | 'ipd' | 'alert' | string;
  id: string;
  title: string;
  subtitle?: string;
  patient_name?: string | null;
  phone?: string | null;
  status?: string | null;
  date?: string | null;
  time?: string | null;
  notes?: string | null;
  department?: string | null;
  doctor?: string | null;
  service_type?: string | null;
  hospital_id?: string | null;
  media_url?: string | null;
  needs_action?: boolean;
  created_at?: number;
  raw?: Record<string, unknown>;
};

type Props = {
  apiBase: string;
};

const FLOW_FILTERS = [
  { id: 'all', label: 'All', icon: Bell },
  { id: 'opd', label: 'OPD', icon: Stethoscope },
  { id: 'ultrasound', label: 'Ultrasound', icon: ScanLine },
  { id: 'lab', label: 'Lab', icon: TestTube },
  { id: 'pharmacy', label: 'Pharmacy', icon: Pill },
  { id: 'ipd', label: 'IPD', icon: Bed },
];

const QUEUE_FILTERS = [
  { id: 'action', label: 'Needs action' },
  { id: 'today', label: 'Today' },
  { id: 'all', label: 'All' },
];

function flowMeta(flow?: string) {
  switch (flow) {
    case 'opd':
      return { label: 'OPD', color: 'bg-sky-50 text-sky-700 border-sky-200', Icon: Stethoscope };
    case 'ultrasound':
      return { label: 'Ultrasound', color: 'bg-violet-50 text-violet-700 border-violet-200', Icon: ScanLine };
    case 'lab':
      return { label: 'Lab', color: 'bg-amber-50 text-amber-700 border-amber-200', Icon: TestTube };
    case 'pharmacy':
      return { label: 'Pharmacy', color: 'bg-emerald-50 text-emerald-700 border-emerald-200', Icon: Pill };
    case 'ipd':
      return { label: 'IPD', color: 'bg-rose-50 text-rose-700 border-rose-200', Icon: Bed };
    default:
      return { label: 'Alert', color: 'bg-slate-100 text-slate-600 border-slate-200', Icon: Bell };
  }
}

function formatWhen(ts?: number) {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

function formatPhone(phone?: string | null) {
  if (!phone) return '';
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 12 && digits.startsWith('91')) {
    return `+91 ${digits.slice(2, 7)} ${digits.slice(7)}`;
  }
  if (digits.length === 10) return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
  return phone;
}

function waLink(phone?: string | null) {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, '');
  if (!digits) return null;
  const full = digits.length === 10 ? `91${digits}` : digits;
  return `https://wa.me/${full}`;
}

function telLink(phone?: string | null) {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, '');
  if (!digits) return null;
  const local = digits.length === 12 && digits.startsWith('91') ? digits.slice(2) : digits;
  return `tel:+91${local.length === 10 ? local : digits}`;
}

function isOpenStatus(item: StaffRequestItem) {
  const s = (item.status || '').toLowerCase();
  if (item.kind === 'notification') return s === 'unread';
  if (item.kind === 'pharmacy') return s === 'pending' || s === 'open' || !s;
  if (item.kind === 'enquiry') return s === 'open' || s === 'pending' || !s;
  if (item.kind === 'appointment') return s === 'confirmed' || s === 'pending' || !s;
  return !!item.needs_action;
}

export default function StaffRequests({ apiBase }: Props) {
  const [items, setItems] = useState<StaffRequestItem[]>([]);
  const [flow, setFlow] = useState('all');
  const [queue, setQueue] = useState('action');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const fetchFeed = useCallback(async () => {
    try {
      setError('');
      const res = await axios.get(`${apiBase}/api/staff/requests`, {
        params: { limit: 250, flow, queue },
      });
      setItems(res.data || []);
    } catch (e: any) {
      setError(e?.response?.data?.error || e.message || 'Failed to load requests');
    } finally {
      setLoading(false);
    }
  }, [apiBase, flow, queue]);

  useEffect(() => {
    setLoading(true);
    fetchFeed();
    const t = setInterval(fetchFeed, 12000);
    return () => clearInterval(t);
  }, [fetchFeed]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      const hay = [
        item.patient_name, item.phone, item.title, item.subtitle,
        item.id, item.notes, item.department, item.doctor, item.service_type,
      ].filter(Boolean).join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [items, search]);

  const summary = useMemo(() => {
    const open = items.filter(isOpenStatus).length;
    const today = new Date().toISOString().slice(0, 10);
    const todayCount = items.filter((i) => i.date === today).length;
    const byFlow: Record<string, number> = {};
    for (const item of items) {
      const f = item.flow || 'alert';
      byFlow[f] = (byFlow[f] || 0) + 1;
    }
    return { open, todayCount, byFlow, total: items.length };
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
    <div className="space-y-5">
      {/* Summary strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Needs action', value: summary.open, tone: 'text-amber-700 bg-amber-50 border-amber-100' },
          { label: "Today's bookings", value: summary.todayCount, tone: 'text-sky-700 bg-sky-50 border-sky-100' },
          { label: 'Pharmacy', value: summary.byFlow.pharmacy || 0, tone: 'text-emerald-700 bg-emerald-50 border-emerald-100' },
          { label: 'IPD enquiries', value: summary.byFlow.ipd || 0, tone: 'text-rose-700 bg-rose-50 border-rose-100' },
        ].map((card) => (
          <div key={card.label} className={`rounded-2xl border px-4 py-3 ${card.tone}`}>
            <p className="text-xs font-semibold uppercase tracking-wide opacity-80">{card.label}</p>
            <p className="text-2xl font-bold mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-slate-800">Front Desk Inbox</h3>
          <p className="text-sm text-slate-500">
            Sudha WhatsApp: OPD · Ultrasound · Lab · Pharmacy · IPD
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={markAllRead}
            className="px-3 py-2 rounded-xl border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            Clear alerts
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

      {/* Queue + search */}
      <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          {QUEUE_FILTERS.map((q) => (
            <button
              key={q.id}
              onClick={() => setQueue(q.id)}
              className={`px-3 py-2 rounded-xl text-sm font-semibold border transition ${
                queue === q.id
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {q.label}
            </button>
          ))}
        </div>
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, phone, ref…"
            className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
          />
        </div>
      </div>

      {/* Flow chips matching WhatsApp menu */}
      <div className="flex flex-wrap gap-2">
        {FLOW_FILTERS.map((f) => {
          const Icon = f.icon;
          return (
            <button
              key={f.id}
              onClick={() => setFlow(f.id)}
              className={`px-3 py-2 rounded-full text-sm font-medium border inline-flex items-center gap-1.5 ${
                flow === f.id
                  ? 'bg-cyan-600 text-white border-cyan-600'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <Icon size={14} />
              {f.label}
              {f.id !== 'all' && summary.byFlow[f.id] ? ` (${summary.byFlow[f.id]})` : ''}
            </button>
          );
        })}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {loading && items.length === 0 ? (
          <div className="p-10 text-center text-slate-500">Loading front desk queue…</div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-slate-500">
            {queue === 'action'
              ? 'Nothing pending. New WhatsApp bookings will show here.'
              : 'No requests in this view.'}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((item) => {
              const meta = flowMeta(item.flow);
              const Icon = meta.Icon;
              const busy = busyId === item.id;
              const open = isOpenStatus(item);
              const callHref = telLink(item.phone);
              const chatHref = waLink(item.phone);

              return (
                <div
                  key={`${item.kind}-${item.id}`}
                  className={`p-4 md:p-5 transition ${open ? 'bg-white hover:bg-slate-50/80' : 'bg-slate-50/40'}`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-start gap-4 justify-between">
                    <div className="flex gap-3 min-w-0">
                      <div className={`w-11 h-11 rounded-xl border flex items-center justify-center shrink-0 ${meta.color}`}>
                        <Icon size={20} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-slate-800 text-base">
                            {item.patient_name || item.title}
                          </p>
                          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${meta.color}`}>
                            {meta.label}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full inline-flex items-center gap-1 font-medium ${
                            open ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
                          }`}>
                            <Clock size={12} />
                            {item.status || 'open'}
                          </span>
                        </div>

                        <p className="text-sm text-slate-600 mt-1">
                          {item.title}
                          {item.subtitle ? ` · ${item.subtitle}` : ''}
                        </p>

                        <div className="mt-2 text-sm text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
                          {item.phone && (
                            <span>Phone: <b className="text-slate-700">{formatPhone(item.phone)}</b></span>
                          )}
                          {item.date && (
                            <span>Date: <b className="text-slate-700">{item.date}</b></span>
                          )}
                          {item.time && (
                            <span>Time: <b className="text-slate-700">{item.time}</b></span>
                          )}
                          {item.hospital_id && (
                            <span>Hospital ID: <b className="text-slate-700">{item.hospital_id}</b></span>
                          )}
                          <span>Ref: <b className="text-slate-700">{item.id}</b></span>
                          <span>{formatWhen(item.created_at)}</span>
                        </div>

                        {item.notes && (
                          <p className="mt-2 text-sm text-slate-600 bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 whitespace-pre-wrap">
                            {item.notes}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2 shrink-0 lg:justify-end">
                      {callHref && (
                        <a
                          href={callHref}
                          className="px-3 py-2 rounded-lg border border-slate-200 text-slate-700 text-sm font-medium inline-flex items-center gap-1.5 hover:bg-slate-50"
                        >
                          <Phone size={14} /> Call
                        </a>
                      )}
                      {chatHref && (
                        <a
                          href={chatHref}
                          target="_blank"
                          rel="noreferrer"
                          className="px-3 py-2 rounded-lg border border-emerald-200 text-emerald-700 text-sm font-medium inline-flex items-center gap-1.5 hover:bg-emerald-50"
                        >
                          <MessageCircle size={14} /> WhatsApp
                        </a>
                      )}

                      {item.kind === 'enquiry' && open && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'closed')}
                          className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50 inline-flex items-center gap-1"
                        >
                          <CheckCircle2 size={14} /> Mark closed
                        </button>
                      )}
                      {item.kind === 'pharmacy' && open && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'done')}
                          className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50 inline-flex items-center gap-1"
                        >
                          <CheckCircle2 size={14} /> Mark done
                        </button>
                      )}
                      {item.kind === 'appointment' && open && (
                        <button
                          disabled={busy}
                          onClick={() => updateStatus(item, 'completed')}
                          className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50 inline-flex items-center gap-1"
                        >
                          <CheckCircle2 size={14} /> Complete
                        </button>
                      )}
                      {item.kind === 'notification' && open && (
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
