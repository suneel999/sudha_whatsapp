import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Users, Calendar, Activity, MessageSquare, Search, Bell,
  LayoutDashboard, ChevronRight, RefreshCcw, Send, CheckCircle2,
  Clock, Phone, Heart, Brain, Stethoscope,
  AlertCircle, X, Eye, CalendarDays, MessageCircle,
  Building2, TestTube, Bed, Lock, Instagram, Facebook, LogOut
} from 'lucide-react';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import LoginForm from './components/LoginForm';
import StaffRequests from './components/StaffRequests';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://chat.sudhahospitalkphb.com';

// Types - Updated to match new API
interface Stats {
  total_patients: number;
  total_appointments: number;
  total_diagnostics: number;
  total_admissions: number;
  pending_admissions: number;
  today_appointments: number;
  today_diagnostics: number;
  recent_activity: number;
  new_patients_week: number;
  platforms: Record<string, number>;
  departments: Record<string, number>;
  test_types: Record<string, number>;
  total_enquiries?: number;
  open_enquiries?: number;
  total_pharmacy?: number;
  pending_pharmacy?: number;
  unread_notifications?: number;
}

interface Patient {
  id: number;
  external_id: string;
  platform: string;
  hospital_patient_id?: string | null;
  automation_paused?: number | boolean;
  name: string | null;
  phone: string | null;
  email: string | null;
  first_touch: number;
  last_touch: number;
  total_bookings: number;
  total_appointments: number;
  total_diagnostics: number;
  total_admissions: number;
  notes: string | null;
}

interface Appointment {
  booking_id: string;
  user_id: string;
  patient_name: string;
  patient_identifier?: string | null;
  phone: string;
  department: string;
  department_name: string;
  doctor: string;
  date: string;
  time: string;
  status: string;
  cancel_reason?: string | null;
  cancelled_by?: string | null;
  cancelled_at?: number | null;
  source: string;
  created_at: number;
}

interface Diagnostic {
  booking_id: string;
  user_id: string;
  patient_name: string;
  phone: string;
  test_type: string;
  date: string;
  time: string;
  status: string;
  created_at: number;
}

interface Admission {
  admission_id: string;
  user_id: string;
  patient_name: string;
  phone: string;
  age: string;
  sex: string;
  admission_type: string;
  preferred_date: string;
  status: string;
  created_at: number;
}

interface Interaction {
  id: number;
  patient_id: number;
  user_id: string;
  direction: string;
  platform: string;
  message: string;
  message_type: string;
  timestamp: number;
  patient_name?: string;
  external_id?: string;
}

interface AppNotification {
  id: string;
  type: 'appointment' | 'diagnostic' | 'admission' | 'interaction';
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  patientName?: string;
  source?: string;
}

// Colors for charts
const COLORS = ['#0891b2', '#6366f1', '#10b981', '#f59e0b', '#ef4444'];

// Channel/platform display: WhatsApp, Instagram, Facebook
const PLATFORM_CONFIG: Record<string, { label: string; short: string; icon: any; color: string; className: string; bgClass: string; badgeClass: string }> = {
  whatsapp: {
    label: 'WhatsApp',
    short: 'WA',
    icon: MessageCircle,
    color: '#10b981',
    className: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    bgClass: 'bg-emerald-500',
    badgeClass: 'glass-badge-wa'
  },
  instagram: {
    label: 'Instagram',
    short: 'IG',
    icon: Instagram,
    color: '#d946ef',
    className: 'bg-pink-100 text-pink-700 border-pink-200',
    bgClass: 'bg-gradient-to-br from-purple-500 to-pink-500',
    badgeClass: 'glass-badge-ig'
  },
  facebook: {
    label: 'Facebook',
    short: 'FB',
    icon: Facebook,
    color: '#3b82f6',
    className: 'bg-blue-100 text-blue-700 border-blue-200',
    bgClass: 'bg-blue-600',
    badgeClass: 'glass-badge-fb'
  },
};

function getPlatformDisplay(platform: string) {
  const key = (platform || 'whatsapp').toLowerCase();
  return PLATFORM_CONFIG[key] || PLATFORM_CONFIG.whatsapp;
}

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('requests');
  const [stats, setStats] = useState<Stats | null>(null);
  const [weeklyData, setWeeklyData] = useState<any[]>([]);
  const [liveFeed, setLiveFeed] = useState<Interaction[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([]);
  const [admissions, setAdmissions] = useState<Admission[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [patientTimeline, setPatientTimeline] = useState<Interaction[]>([]);
  const [appointmentFilter, setAppointmentFilter] = useState('all');
  const [appointmentSourceFilter, setAppointmentSourceFilter] = useState('all'); // whatsapp, instagram, facebook
  const [patientPlatformFilter, setPatientPlatformFilter] = useState('all');
  const [patientSort, setPatientSort] = useState<'recent' | 'bookings'>('recent');
  const [appointmentDateFilter, setAppointmentDateFilter] = useState('all'); // all, today, yesterday, last7days
  const [doctorFilter, setDoctorFilter] = useState('all');
  const [appointmentSort, setAppointmentSort] = useState<'schedule_asc' | 'schedule_desc' | 'booked_newest' | 'booked_oldest'>('schedule_asc');
  const [notificationFilter, setNotificationFilter] = useState<'all' | 'unread'>('all');
  const [showPatientModal, setShowPatientModal] = useState(false);
  const [hospitalPatientIdInput, setHospitalPatientIdInput] = useState('');
  const [savingHospitalPatientId, setSavingHospitalPatientId] = useState(false);
  const [updatingAutomation, setUpdatingAutomation] = useState(false);
  const [whatsappMessageInput, setWhatsappMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(() => new Date());
  const [calendarSelectedDate, setCalendarSelectedDate] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [toasts, setToasts] = useState<AppNotification[]>([]);

  // Storage for last processed IDs to avoid duplicate notifications
  const lastProcessedIds = useRef({
    appointments: new Set<string>(),
    diagnostics: new Set<string>(),
    admissions: new Set<string>(),
    interactions: 0 // Using ID for interactions
  });

  const chatMessagesEndRef = useRef<HTMLDivElement>(null);

  // AUTH STATE
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('crm_token'));
  const [user, setUser] = useState<any | null>(() => {
    const saved = localStorage.getItem('crm_user');
    return saved ? JSON.parse(saved) : null;
  });

  // AXIOS INTERCEPTOR FOR AUTH
  useEffect(() => {
    const interceptor = axios.interceptors.request.use((config) => {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor to handle 401
    const resInterceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          handleLogout();
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(interceptor);
      axios.interceptors.response.eject(resInterceptor);
    };
  }, [token]);

  const onLoginSuccess = (newToken: string, newUser: any) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('crm_token', newToken);
    localStorage.setItem('crm_user', JSON.stringify(newUser));
  };

  const addNotification = useCallback((notif: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => {
    const newNotif: AppNotification = {
      ...notif,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: Date.now() / 1000,
      read: false
    };
    setNotifications(prev => [newNotif, ...prev].slice(0, 50));
    setToasts(prev => [...prev, newNotif]);

    // Auto-remove toast after 6 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== newNotif.id));
    }, 6000);
  }, []);

  const handleLogout = async () => {
    try {
      await axios.post(`${API_BASE}/api/auth/logout`);
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem('crm_token');
      localStorage.removeItem('crm_user');
    }
  };

  const fetchData = useCallback(async () => {
    try {
      const encodedSearch = encodeURIComponent(searchTerm || '');
      const [statsRes, weeklyRes, feedRes, patientsRes, appointmentsRes, diagnosticsRes, admissionsRes] = await Promise.all([
        axios.get(`${API_BASE}/api/stats`),
        axios.get(`${API_BASE}/api/analytics/weekly`),
        axios.get(`${API_BASE}/api/live-feed?limit=15`),
        axios.get(`${API_BASE}/api/patients?search=${encodedSearch}&limit=50&platform=${patientPlatformFilter}`),
        axios.get(`${API_BASE}/api/appointments?status=${appointmentFilter}&source=${appointmentSourceFilter}&search=${encodedSearch}`),
        axios.get(`${API_BASE}/api/diagnostics`),
        axios.get(`${API_BASE}/api/admissions`)
      ]);

      setStats(statsRes.data);
      setWeeklyData(weeklyRes.data);
      setLiveFeed(feedRes.data);
      setPatients(patientsRes.data);
      setAppointments(appointmentsRes.data);
      setDiagnostics(diagnosticsRes.data);
      setAdmissions(admissionsRes.data);

      // --- NOTIFICATION DETECTION LOGIC ---
      if (!loading) {
        const newAppointments = appointmentsRes.data as Appointment[];
        const newDiagnostics = diagnosticsRes.data as Diagnostic[];
        const newAdmissions = admissionsRes.data as Admission[];

        // Initial tracking setup
        if (lastProcessedIds.current.appointments.size === 0) {
          newAppointments.forEach(a => lastProcessedIds.current.appointments.add(a.booking_id));
          newDiagnostics.forEach(d => lastProcessedIds.current.diagnostics.add(d.booking_id));
          newAdmissions.forEach(a => lastProcessedIds.current.admissions.add(a.admission_id));
        } else {
          // Check for new appointments
          newAppointments.forEach(a => {
            if (!lastProcessedIds.current.appointments.has(a.booking_id)) {
              lastProcessedIds.current.appointments.add(a.booking_id);
              addNotification({
                type: 'appointment',
                title: 'New Appointment',
                message: `${a.patient_name} booked for ${a.doctor} at ${a.time}`,
                patientName: a.patient_name,
                source: a.source
              });
            }
          });

          // Check for new diagnostics
          newDiagnostics.forEach(d => {
            if (!lastProcessedIds.current.diagnostics.has(d.booking_id)) {
              lastProcessedIds.current.diagnostics.add(d.booking_id);
              addNotification({
                type: 'diagnostic',
                title: 'New Diagnostic Booking',
                message: `${d.patient_name} requested a ${d.test_type}`,
                patientName: d.patient_name,
                source: 'whatsapp'
              });
            }
          });

          // Check for new admissions
          newAdmissions.forEach(a => {
            if (!lastProcessedIds.current.admissions.has(a.admission_id)) {
              lastProcessedIds.current.admissions.add(a.admission_id);
              addNotification({
                type: 'admission',
                title: 'New Admission Request',
                message: `${a.patient_name} (${a.admission_type})`,
                patientName: a.patient_name,
                source: 'whatsapp'
              });
            }
          });
        }
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setLoading(false);
    }
  }, [searchTerm, appointmentFilter, appointmentSourceFilter, patientPlatformFilter, loading, addNotification]);

  useEffect(() => {
    if (token) {
      fetchData();
      const interval = setInterval(fetchData, 15000);
      return () => clearInterval(interval);
    }
  }, [fetchData, token]);

  const fetchPatientDetail = async (patient: Patient) => {
    try {
      const res = await axios.get(`${API_BASE}/api/patients/${patient.id}/timeline`);
      setSelectedPatient(patient);
      setPatientTimeline(res.data.interactions || []);
      setShowPatientModal(false);
      setWhatsappMessageInput('');
    } catch (err) {
      console.error('Error fetching patient details:', err);
    }
  };

  useEffect(() => {
    if (selectedPatient) {
      setHospitalPatientIdInput(selectedPatient.hospital_patient_id || '');
    }
  }, [selectedPatient]);

  const sendWhatsAppMessage = async () => {
    if (!selectedPatient || !whatsappMessageInput.trim()) return;
    setSendingMessage(true);
    try {
      await axios.post(`${API_BASE}/api/send-message`, {
        patient_id: selectedPatient.id,
        message: whatsappMessageInput.trim()
      });
      setWhatsappMessageInput('');
      const res = await axios.get(`${API_BASE}/api/patients/${selectedPatient.id}/timeline`);
      setPatientTimeline(res.data.interactions || []);
    } catch (err) {
      console.error('Error sending message:', err);
    } finally {
      setSendingMessage(false);
    }
  };

  // Scroll chat to bottom when conversation or messages change (show latest messages)
  useEffect(() => {
    if (selectedPatient && patientTimeline.length > 0) {
      chatMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [selectedPatient?.id, patientTimeline.length]);

  const updateAppointmentStatus = async (bookingId: string, status: string) => {
    try {
      await axios.put(`${API_BASE}/api/appointments/${bookingId}/status`, { status });
      fetchData();
    } catch (err) {
      console.error('Error updating appointment:', err);
    }
  };

  const cancelAppointment = async (bookingId: string) => {
    const reason = window.prompt('Reason for cancellation (optional):') || '';
    try {
      await axios.post(`${API_BASE}/api/appointments/${bookingId}/cancel`, {
        reason: reason.trim(),
        cancelled_by: 'staff'
      });
      fetchData();
    } catch (err) {
      console.error('Error cancelling appointment:', err);
    }
  };

  const updateDiagnosticStatus = async (bookingId: string, status: string) => {
    try {
      await axios.put(`${API_BASE}/api/diagnostics/${bookingId}/status`, { status });
      fetchData();
    } catch (err) {
      console.error('Error updating diagnostic:', err);
    }
  };

  const updateAdmissionStatus = async (admissionId: string, status: string) => {
    try {
      await axios.put(`${API_BASE}/api/admissions/${admissionId}/status`, { status });
      fetchData();
    } catch (err) {
      console.error('Error updating admission:', err);
    }
  };

  const saveHospitalPatientId = async () => {
    if (!selectedPatient || !hospitalPatientIdInput.trim()) return;
    setSavingHospitalPatientId(true);
    try {
      await axios.put(`${API_BASE}/api/patients/${selectedPatient.id}/hospital-id`, {
        hospital_patient_id: hospitalPatientIdInput.trim()
      });
      await fetchData();
      setSelectedPatient((prev) => prev ? { ...prev, hospital_patient_id: hospitalPatientIdInput.trim() } : prev);
    } catch (err) {
      console.error('Error saving hospital patient ID:', err);
    } finally {
      setSavingHospitalPatientId(false);
    }
  };

  const isAutomationPaused = (patient?: Patient | null): boolean => {
    if (!patient) return false;
    return patient.automation_paused === true || patient.automation_paused === 1;
  };

  const togglePatientAutomation = async () => {
    if (!selectedPatient) return;
    const paused = !isAutomationPaused(selectedPatient);
    setUpdatingAutomation(true);
    try {
      await axios.put(`${API_BASE}/api/patients/${selectedPatient.id}/automation`, { paused });
      setSelectedPatient(prev => prev ? { ...prev, automation_paused: paused ? 1 : 0 } : prev);
      setPatients(prev => prev.map(p => p.id === selectedPatient.id ? { ...p, automation_paused: paused ? 1 : 0 } : p));
    } catch (err) {
      console.error('Error updating automation status:', err);
    } finally {
      setUpdatingAutomation(false);
    }
  };

  const getPatientDisplayName = (patient: Patient): string =>
    patient.name && patient.name.toLowerCase() !== 'anonymous'
      ? patient.name
      : 'Unknown Patient';

  const getPatientDisplayNumber = (patient: Patient): string => {
    if (patient.phone) return patient.phone;
    if ((patient.platform || '').toLowerCase() === 'whatsapp' && patient.external_id) return patient.external_id;
    return '--';
  };

  const formatTime = (timestamp: number) => {
    if (!timestamp) return '--';
    return new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: number) => {
    if (!timestamp) return '--';
    return new Date(timestamp * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  };

  const formatDateTime = (timestamp: number) => {
    if (!timestamp) return '--';
    return new Date(timestamp * 1000).toLocaleString('en-GB', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const finalizeNextAppointment = async () => {
    if (frontDeskQueue.length === 0) return;
    await updateAppointmentStatus(frontDeskQueue[0].booking_id, 'completed');
  };

  const formatAppointmentDate = (dateStr?: string) => {
    if (!dateStr) return '--';
    const parsed = new Date(dateStr);
    if (Number.isNaN(parsed.getTime())) return dateStr;
    return parsed.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const markNotificationAsRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const clearReadNotifications = () => {
    setNotifications(prev => prev.filter(n => !n.read));
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  /** Format timestamp to relative time (Just now, 2h ago, etc) */
  const formatRelativeTime = (timestamp: number) => {
    if (!timestamp) return '--';
    const now = Date.now() / 1000;
    const diff = now - timestamp;

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 172800) return 'Yesterday';
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;

    return new Date(timestamp * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  };

  /** Parse CRM message: show text + options (handles legacy JSON/dict strings). */
  const parseMessageDisplay = (raw: string): { text: string; options?: string[] } => {
    if (!raw || typeof raw !== 'string') return { text: raw || '' };
    const s = raw.trim();
    if (s.includes('Options: ')) {
      const idx = s.indexOf('Options: ');
      return { text: s.slice(0, idx).trim(), options: s.slice(idx + 9).split(', ').map((x) => x.trim()).filter(Boolean) };
    }
    if (s.startsWith('{') && (s.includes('text') || s.includes('buttons'))) {
      try {
        const jsonStr = s.replace(/'/g, '"').replace(/(\w+):/g, '"$1":');
        const json = JSON.parse(jsonStr);
        const text = (json.text || '').trim();
        const buttons = json.buttons as Array<{ title?: string; id?: string }> | undefined;
        const options = buttons?.map((b) => (b.title || b.id || '').trim()).filter(Boolean) as string[] | undefined;
        return { text: text || 'Message sent', options };
      } catch {
        const textMatch = s.match(/'text'\s*:\s*["']((?:[^"']|\n)*)["']/);
        const text = textMatch ? textMatch[1] : s;
        const titleMatches = s.match(/'title'\s*:\s*["']([^"']*)["']/g) || [];
        const options = titleMatches.map((x) => x.replace(/'title'\s*:\s*["']([^"']*)["']/, '$1').replace(/^.*["']([^"']+)["']\s*$/, '$1'));
        return { text: text || s, options: options.length ? options : undefined };
      }
    }
    return { text: s };
  };

  /** Format message for display: parse dict-like strings, normalize \\n to newlines, return content for pre-line rendering. */
  const formatMessageForDisplay = (raw: string): { text: string; options?: string[] } => {
    const parsed = parseMessageDisplay(raw || '');
    const text = (parsed.text || '').replace(/\\n/g, '\n');
    return { text, options: parsed.options };
  };

  const getStatusBadge = (status: string) => {
    const s = (status || '').toLowerCase();
    const badges: Record<string, string> = {
      confirmed: 'glass-badge-success',
      completed: 'glass-badge-info',
      cancelled: 'glass-badge-danger',
      'no-show': 'glass-badge-warning',
      pending: 'glass-badge-warning',
      admitted: 'glass-badge-info',
      discharged: 'glass-badge-default'
    };
    return `glass-badge ${badges[s] || 'glass-badge-default'}`;
  };

  const getDeptIcon = (dept: string) => {
    if (!dept) return <Stethoscope size={16} />;
    if (dept.toLowerCase().includes('cardio') || dept.toLowerCase().includes('heart')) return <Heart size={16} />;
    if (dept.toLowerCase().includes('neuro') || dept.toLowerCase().includes('brain')) return <Brain size={16} />;
    return <Stethoscope size={16} />;
  };

  // Prepare pie chart data
  const pieData = stats ? Object.entries(stats.departments || {}).map(([name, value]) => ({ name, value })) : [];

  const toIsoDate = (input?: string | null): string => {
    if (!input) return '';
    const raw = input.trim();
    if (!raw) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    const parsed = new Date(raw);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().split('T')[0];
    return '';
  };

  const parseSlotToMinutes = (slot?: string | null): number => {
    if (!slot) return Number.MAX_SAFE_INTEGER;
    const s = slot.trim().toUpperCase();
    const m = s.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/);
    if (!m) return Number.MAX_SAFE_INTEGER;
    let hours = parseInt(m[1], 10);
    const minutes = parseInt(m[2], 10);
    const meridiem = m[3];
    if (meridiem === 'PM' && hours !== 12) hours += 12;
    if (meridiem === 'AM' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  };

  const todayIso = new Date().toISOString().split('T')[0];
  const todayScheduledAppointments = appointments
    .filter((a) => toIsoDate(a.date) === todayIso && a.status.toLowerCase() !== 'cancelled')
    .sort((a, b) => (a.time || '').localeCompare(b.time || ''));

  const todayBookedAppointments = appointments
    .filter((a) => {
      if (!a.created_at) return false;
      const createdIso = new Date(a.created_at * 1000).toISOString().split('T')[0];
      return createdIso === todayIso;
    })
    .sort((a, b) => (b.created_at || 0) - (a.created_at || 0));

  // Get unique doctors for filtering
  const doctorList = Array.from(new Set(appointments.map(a => a.doctor).filter(Boolean)));

  // Filter and Sort Patients
  const filteredPatients = [...patients]
    .sort((a, b) => {
      if (patientSort === 'recent') return (b.last_touch || 0) - (a.last_touch || 0);
      return ((b.total_appointments || 0) + (b.total_diagnostics || 0)) - ((a.total_appointments || 0) + (a.total_diagnostics || 0));
    });

  // Filter + sort appointments for operations view
  const filteredAppointments = appointments.filter(appt => {
    // Status Filter
    if (appointmentFilter !== 'all' && appt.status.toLowerCase() !== appointmentFilter.toLowerCase()) return false;

    // Source Filter
    if (appointmentSourceFilter !== 'all' && (appt.source || 'whatsapp').toLowerCase() !== appointmentSourceFilter.toLowerCase()) return false;

    // Doctor Filter
    if (doctorFilter !== 'all' && appt.doctor !== doctorFilter) return false;

    // Date Filter
    if (appointmentDateFilter !== 'all') {
      const apptDate = toIsoDate(appt.date);
      const today = new Date().toISOString().split('T')[0];
      const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];

      if (appointmentDateFilter === 'today' && apptDate !== today) return false;
      if (appointmentDateFilter === 'yesterday' && apptDate !== yesterday) return false;
      if (appointmentDateFilter === 'last7days') {
        const diff = (new Date(today).getTime() - new Date(apptDate).getTime()) / 86400000;
        if (diff > 7 || diff < 0) return false;
      }
    }

    return true;
  }).sort((a, b) => {
    const dateA = toIsoDate(a.date) || '9999-12-31';
    const dateB = toIsoDate(b.date) || '9999-12-31';
    const timeA = parseSlotToMinutes(a.time);
    const timeB = parseSlotToMinutes(b.time);

    if (appointmentSort === 'schedule_desc') {
      if (dateA !== dateB) return dateB.localeCompare(dateA);
      return timeB - timeA;
    }

    if (appointmentSort === 'booked_newest') {
      return (b.created_at || 0) - (a.created_at || 0);
    }

    if (appointmentSort === 'booked_oldest') {
      return (a.created_at || 0) - (b.created_at || 0);
    }

    // schedule_asc
    if (dateA !== dateB) return dateA.localeCompare(dateB);
    return timeA - timeB;
  });

  const frontDeskQueue = filteredAppointments
    .filter((a) => toIsoDate(a.date) === todayIso && a.status.toLowerCase() === 'confirmed')
    .sort((a, b) => parseSlotToMinutes(a.time) - parseSlotToMinutes(b.time));

  const visibleNotifications = notificationFilter === 'unread'
    ? notifications.filter((n) => !n.read)
    : notifications;

  if (!token) {
    return <LoginForm onLoginSuccess={onLoginSuccess} apiBase={API_BASE} />;
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-72 sidebar-gradient fixed h-screen flex flex-col text-white">
        {/* Logo */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur">
              <Building2 size={28} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Sudha</h1>
              <p className="text-xs text-cyan-100 font-medium">Hospital CRM</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {[
            { id: 'requests', icon: Bell, label: 'Staff Requests' },
            { id: 'overview', icon: LayoutDashboard, label: 'Dashboard' },
            { id: 'patients', icon: Users, label: 'Patients' },
            { id: 'appointments', icon: Calendar, label: 'Appointments' },
            { id: 'calendar', icon: CalendarDays, label: 'Calendar' },
            { id: 'diagnostics', icon: TestTube, label: 'Diagnostics' },
            { id: 'admissions', icon: Bed, label: 'Admissions' },
            { id: 'omnichannel', icon: MessageSquare, label: 'Messages' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all ${activeTab === item.id
                ? 'bg-white text-cyan-700 shadow-lg shadow-black/10 font-semibold'
                : 'text-white/80 hover:bg-white/10'
                }`}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
              {activeTab === item.id && <ChevronRight size={16} className="ml-auto" />}
            </button>
          ))}
        </nav>


        {/* User Profile */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center font-bold">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold truncate">{user?.full_name || user?.username || 'User'}</p>
              <p className="text-xs text-cyan-100 opacity-70 uppercase tracking-tighter">{user?.role || 'Staff'}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all font-medium text-sm border border-transparent hover:border-white/10"
          >
            <Lock size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-72">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-lg border-b border-slate-100 px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-cyan-600 uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Live Dashboard
              </p>
              <h2 className="text-2xl font-bold text-slate-800 mt-1">
                {activeTab === 'requests' && 'Staff Requests Inbox'}
                {activeTab === 'overview' && 'Dashboard Overview'}
                {activeTab === 'patients' && 'Patient Directory'}
                {activeTab === 'appointments' && 'Appointment Manager'}
                {activeTab === 'diagnostics' && 'Diagnostic Bookings'}
                {activeTab === 'admissions' && 'Admission Requests'}
                {activeTab === 'omnichannel' && 'Messages (WhatsApp, Instagram, Facebook)'}
                {activeTab === 'calendar' && 'Appointments Calendar'}
              </h2>
            </div>

            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  type="text"
                  placeholder="Search patients, appointments..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input pl-10 w-72"
                />
              </div>
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className={`btn btn-ghost relative ${showNotifications ? 'bg-slate-100' : ''}`}
                >
                  <Bell size={20} className={unreadCount > 0 ? 'text-cyan-600' : 'text-slate-600'} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-rose-500 rounded-full text-[10px] text-white font-bold flex items-center justify-center border-2 border-white animate-bounce-slow">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {/* Notifications Dropdown */}
                <AnimatePresence>
                  {showNotifications && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setShowNotifications(false)}
                      />
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-2xl border border-slate-100 z-50 overflow-hidden"
                      >
                        <div className="p-4 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
                          <h3 className="font-bold text-slate-800 flex items-center gap-2">
                            Notifications
                            {unreadCount > 0 && <span className="bg-cyan-100 text-cyan-700 text-[10px] px-2 py-0.5 rounded-full uppercase">{unreadCount} New</span>}
                          </h3>
                          <div className="flex items-center gap-3">
                            <button
                              onClick={clearReadNotifications}
                              className="text-[10px] font-bold text-slate-500 uppercase hover:underline"
                            >
                              Clear Read
                            </button>
                            <button
                              onClick={markAllAsRead}
                              className="text-[10px] font-bold text-cyan-600 uppercase hover:underline"
                            >
                              Mark all read
                            </button>
                          </div>
                        </div>
                        <div className="px-4 py-2 border-b border-slate-50 bg-white flex items-center gap-2">
                          <button
                            onClick={() => setNotificationFilter('all')}
                            className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide ${notificationFilter === 'all' ? 'bg-cyan-100 text-cyan-700' : 'bg-slate-100 text-slate-500'}`}
                          >
                            All
                          </button>
                          <button
                            onClick={() => setNotificationFilter('unread')}
                            className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide ${notificationFilter === 'unread' ? 'bg-cyan-100 text-cyan-700' : 'bg-slate-100 text-slate-500'}`}
                          >
                            Unread ({unreadCount})
                          </button>
                        </div>
                        <div className="max-h-[400px] overflow-y-auto">
                          {visibleNotifications.length > 0 ? (
                            visibleNotifications.map(n => (
                              <div
                                key={n.id}
                                className={`p-4 border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors cursor-pointer ${!n.read ? 'bg-cyan-50/30' : ''}`}
                                onClick={() => {
                                  markNotificationAsRead(n.id);
                                  if (n.type === 'appointment') setActiveTab('appointments');
                                  if (n.type === 'diagnostic') setActiveTab('diagnostics');
                                  if (n.type === 'admission') setActiveTab('admissions');
                                  setShowNotifications(false);
                                }}
                              >
                                <div className="flex gap-3">
                                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${n.type === 'appointment' ? 'bg-cyan-100 text-cyan-600' :
                                    n.type === 'diagnostic' ? 'bg-emerald-100 text-emerald-600' :
                                      'bg-amber-100 text-amber-600'
                                    }`}>
                                    {n.type === 'appointment' && <Calendar size={18} />}
                                    {n.type === 'diagnostic' && <TestTube size={18} />}
                                    {n.type === 'admission' && <Bed size={18} />}
                                  </div>
                                  <div className="min-w-0">
                                    <p className="text-sm font-bold text-slate-800 truncate">{n.title}</p>
                                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>                                    <div className="flex items-center justify-between mt-2 gap-2">
                                      <p className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
                                        <Clock size={10} /> {formatRelativeTime(n.timestamp)} ? {n.source || 'WhatsApp'}
                                      </p>
                                      {!n.read && (
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            markNotificationAsRead(n.id);
                                          }}
                                          className="text-[10px] font-bold text-cyan-600 uppercase hover:underline"
                                        >
                                          Mark Read
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="p-8 text-center text-slate-400">
                              <Bell size={32} className="mx-auto mb-2 opacity-20" />
                              <p className="text-sm font-medium">No notifications yet</p>
                            </div>
                          )}
                        </div>
                        <div className="p-3 bg-slate-50/50 text-center border-t border-slate-50">
                          <button className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-600">
                            Viewing Recent Activity
                          </button>
                        </div>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
              <button onClick={fetchData} className="btn btn-secondary">
                <RefreshCcw size={16} /> Refresh
              </button>
              <button onClick={handleLogout} className="btn bg-rose-50 text-rose-600 hover:bg-rose-600 hover:text-white border-transparent flex items-center gap-2 ml-2 transition-all">
                <LogOut size={16} /> Logout
              </button>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-[60vh]">
              <RefreshCcw className="animate-spin text-cyan-600 mb-4" size={48} />
              <p className="text-slate-400 font-medium">Loading dashboard...</p>
            </div>
          ) : (
            <AnimatePresence mode="wait">
              {/* STAFF REQUESTS INBOX */}
              {activeTab === 'requests' && (
                <motion.div
                  key="requests"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <StaffRequests apiBase={API_BASE} />
                </motion.div>
              )}

              {/* OVERVIEW TAB */}
              {activeTab === 'overview' && (
                <motion.div
                  key="overview"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-8"
                >
                  {/* Stats Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
                    {[
                      { label: 'Total Patients', value: stats?.total_patients || 0, icon: Users, color: 'cyan' },
                      { label: 'Appointments', value: stats?.total_appointments || 0, icon: Calendar, color: 'indigo' },
                      { label: 'Open Enquiries', value: stats?.open_enquiries || 0, icon: Bed, color: 'amber' },
                      { label: 'Pharmacy Pending', value: stats?.pending_pharmacy || 0, icon: Activity, color: 'emerald' },
                      { label: "Today's Appts", value: stats?.today_appointments || 0, icon: CalendarDays, color: 'rose' },
                      { label: 'Unread Alerts', value: stats?.unread_notifications || 0, icon: Bell, color: 'violet' },
                    ].map((stat, idx) => (
                      <div key={idx} className={`stat-card ${stat.color} card-hover`}>
                        <div className="flex justify-between items-start mb-3">
                          <div className={`p-2.5 rounded-xl bg-${stat.color}-50 text-${stat.color}-600`}>
                            <stat.icon size={20} />
                          </div>
                        </div>
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{stat.label}</p>
                        <h3 className="text-2xl font-bold text-slate-800 mt-1">{stat.value}</h3>
                      </div>
                    ))}
                  </div>

                  {/* Channels breakdown - WhatsApp, Instagram, Facebook */}
                  {stats?.platforms && Object.keys(stats.platforms).length > 0 && (
                    <div className="card p-6">
                      <h3 className="font-bold text-slate-800 mb-4">Patients by Channel</h3>
                      <div className="flex flex-wrap gap-4">
                        {['whatsapp', 'instagram', 'facebook'].map((key) => {
                          const count = stats.platforms[key] || 0;
                          const cfg = getPlatformDisplay(key);
                          return (
                            <div key={key} className="flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-50 border border-slate-100">
                              <span className={`w-3 h-3 rounded-full ${cfg.bgClass}`} />
                              <span className="font-semibold text-slate-800">{cfg.label}</span>
                              <span className="text-2xl font-bold text-slate-800">{count}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Charts Row */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Weekly Trend Chart */}
                    <div className="lg:col-span-2 card p-6">
                      <div className="flex justify-between items-center mb-6">
                        <h3 className="font-bold text-slate-800">Weekly Activity Trend</h3>
                        <div className="flex gap-4 text-xs">
                          <span className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-cyan-500"></span> Appointments</span>
                          <span className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-indigo-500"></span> New Patients</span>
                        </div>
                      </div>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={weeklyData}>
                            <defs>
                              <linearGradient id="colorAppt" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#0891b2" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#0891b2" stopOpacity={0} />
                              </linearGradient>
                              <linearGradient id="colorPatients" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                            <Tooltip
                              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.1)' }}
                            />
                            <Area type="monotone" dataKey="appointments" stroke="#0891b2" strokeWidth={2} fill="url(#colorAppt)" />
                            <Area type="monotone" dataKey="new_patients" stroke="#6366f1" strokeWidth={2} fill="url(#colorPatients)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Department Distribution */}
                    <div className="card p-6">
                      <h3 className="font-bold text-slate-800 mb-6">Department Distribution</h3>
                      <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={pieData}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={70}
                              paddingAngle={5}
                              dataKey="value"
                            >
                              {pieData.map((_, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="space-y-2 mt-4">
                        {pieData.slice(0, 4).map((item, idx) => (
                          <div key={idx} className="flex items-center justify-between text-sm">
                            <span className="flex items-center gap-2">
                              <span className="w-3 h-3 rounded" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                              {item.name || 'Other'}
                            </span>
                            <span className="font-bold">{item.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Bottom Row */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                        {/* Today's Schedule */}
                    <div className="card p-6">
                      <div className="flex justify-between items-center mb-6">
                        <h3 className="font-bold text-slate-800">Today's Schedule</h3>
                        <span className="badge badge-info">{todayScheduledAppointments.length} appointments</span>
                      </div>
                      <div className="space-y-3 max-h-72 overflow-y-auto custom-scrollbar">
                        {todayScheduledAppointments.length > 0 ? todayScheduledAppointments.map((appt) => {
                          const src = appt.source || 'whatsapp';
                          const pcfg = getPlatformDisplay(src);
                          return (
                            <div key={appt.booking_id} className="flex items-center gap-4 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors">
                              <div className="w-12 h-12 rounded-xl bg-cyan-100 text-cyan-600 flex items-center justify-center font-bold text-sm">
                                {appt.time?.slice(0, 5) || '--'}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <p className="font-semibold text-slate-800 truncate">{appt.patient_name}</p>
                                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${pcfg.className}`}>{pcfg.short}</span>
                                </div>
                                <p className="text-xs text-slate-500 flex items-center gap-2">
                                  {getDeptIcon(appt.department_name)}
                                  {appt.department_name || 'General'} - {appt.doctor || 'Doctor'}
                                </p>
                                <p className="text-[11px] text-slate-400 mt-1">Booked at: {formatDateTime(appt.created_at)}</p>
                              </div>
                              <span className={`badge ${getStatusBadge(appt.status)}`}>{appt.status}</span>
                            </div>
                          );
                        }) : (
                          <div className="text-center py-8 text-slate-400">
                            <CalendarDays size={40} className="mx-auto mb-2 opacity-50" />
                            <p>No appointments today</p>
                          </div>
                        )}
                      </div>

                      <div className="mt-5 pt-5 border-t border-slate-100">
                        <div className="flex justify-between items-center mb-3">
                          <p className="text-sm font-bold text-slate-700">Booked Today (Placed Time)</p>
                          <span className="badge badge-default">{todayBookedAppointments.length}</span>
                        </div>
                        <div className="space-y-2 max-h-44 overflow-y-auto custom-scrollbar">
                          {todayBookedAppointments.length > 0 ? todayBookedAppointments.map((appt) => (
                            <div key={`placed-${appt.booking_id}`} className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-slate-50">
                              <div className="min-w-0">
                                <p className="text-sm font-semibold text-slate-800 truncate">{appt.patient_name}</p>
                                <p className="text-[11px] text-slate-500 truncate">{appt.booking_id} - {appt.doctor || 'Doctor'}</p>
                              </div>
                              <span className="text-xs font-semibold text-slate-600 whitespace-nowrap">{formatDateTime(appt.created_at)}</span>
                            </div>
                          )) : (
                            <p className="text-sm text-slate-400 text-center py-4">No bookings placed today</p>
                          )}
                        </div>
                      </div>
                    </div>
                    {/* Live Activity Feed */}
                    <div className="card p-6">
                      <div className="flex justify-between items-center mb-6">
                        <h3 className="font-bold text-slate-800">Live Activity</h3>
                        <span className="flex items-center gap-2 text-xs text-emerald-600 font-semibold">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                          Real-time
                        </span>
                      </div>
                      <div className="space-y-4 max-h-96 overflow-y-auto custom-scrollbar pr-2">
                        {liveFeed.length > 0 ? (
                          liveFeed.map((item, idx) => {
                            const { text, options } = formatMessageForDisplay(item.message || '');
                            const pcfg = getPlatformDisplay(item.platform || 'whatsapp');
                            const PlatformIcon = pcfg.icon;

                            return (
                              <div key={item.id || idx} className="glass p-4 rounded-2xl hover:bg-white transition-all group border-slate-100/50">
                                <div className="flex items-center justify-between mb-3">
                                  <div className="flex items-center gap-2">
                                    <div className={`p-1.5 rounded-lg ${pcfg.bgClass} text-white shadow-sm`}>
                                      <PlatformIcon size={12} />
                                    </div>
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{pcfg.label}</span>
                                  </div>
                                  <span className="text-[10px] font-bold text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full uppercase">{formatTime(item.timestamp)}</span>
                                </div>
                                <div className="flex items-start gap-3">
                                  <div className={`p-2.5 rounded-xl ${item.direction === 'inbound' ? 'bg-cyan-50 text-cyan-600' : 'bg-emerald-50 text-emerald-600'}`}>
                                    {item.direction === 'inbound' ? <MessageCircle size={18} /> : <Send size={18} />}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className="font-bold text-slate-800 text-sm truncate">{item.patient_name || 'Patient'}</p>
                                    <p className="text-xs text-slate-500 mt-1 leading-relaxed bg-slate-50/50 p-2 rounded-lg border border-slate-100/50 whitespace-pre-line break-words line-clamp-3 italic">"{text}"</p>
                                    {options && options.length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-2">
                                        {options.map((opt, i) => (
                                          <span key={i} className="text-[10px] font-bold bg-white text-slate-500 border border-slate-100 px-2 py-0.5 rounded-md uppercase tracking-tighter">{opt}</span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                                <div className="mt-3 pt-3 border-t border-slate-50 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={() => {
                                      setActiveTab('omnichannel');
                                      // Find corresponding patient object or create placeholder for type safety
                                      const p = patients.find(pat => pat.external_id === item.external_id) || {
                                        id: 0,
                                        external_id: item.external_id || '',
                                        name: item.patient_name || 'Patient',
                                        platform: item.platform || 'whatsapp'
                                      } as Patient;
                                      fetchPatientDetail(p);
                                    }}
                                    className="text-[10px] font-bold text-cyan-600 uppercase hover:underline flex items-center gap-1"
                                  >
                                    Review & Reply <ChevronRight size={10} />
                                  </button>
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          <div className="text-center py-12 text-slate-400">
                            <Activity size={48} className="mx-auto mb-3 opacity-20" />
                            <p className="font-bold text-slate-500">Waiting for activity...</p>
                            <p className="text-xs mt-1">Real-time messages will appear here.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* PATIENTS TAB */}
              {activeTab === 'patients' && (
                <motion.div
                  key="patients"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-6"
                >
                  <div className="card p-5 bg-gradient-to-r from-cyan-50 to-white border-cyan-100">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <h4 className="font-bold text-slate-800">How Front Office Uses This Screen</h4>
                        <p className="text-sm text-slate-600 mt-1">Find repeat patients, open their full timeline, then jump to chat or appointments in one click.</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => setActiveTab('appointments')} className="btn btn-secondary">
                          <Calendar size={16} /> Open Appointments
                        </button>
                        <button onClick={() => setActiveTab('omnichannel')} className="btn btn-secondary">
                          <MessageSquare size={16} /> Open Messages
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-500 mr-2">Channel:</span>
                      {['all', 'whatsapp', 'instagram', 'facebook'].map((p) => (
                        <button
                          key={p}
                          onClick={() => setPatientPlatformFilter(p)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${patientPlatformFilter === p ? 'bg-cyan-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                        >
                          {p === 'all' ? 'All' : getPlatformDisplay(p).label}
                        </button>
                      ))}
                    </div>
                    <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl">
                      <button
                        onClick={() => setPatientSort('recent')}
                        className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${patientSort === 'recent' ? 'bg-white text-cyan-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                      >
                        Recently Active
                      </button>
                      <button
                        onClick={() => setPatientSort('bookings')}
                        className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${patientSort === 'bookings' ? 'bg-white text-cyan-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                      >
                        Most Bookings
                      </button>
                    </div>
                  </div>
                  <div className="table-container shadow-2xl shadow-slate-200/50">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="border-b border-slate-100/50">
                          <th className="table-header py-5">Name</th>
                          <th className="table-header">Number</th>
                          <th className="table-header">Primary Channel</th>
                          <th className="table-header">Patient ID</th>
                          <th className="table-header">Lifecycle</th>
                          <th className="table-header text-center">Total Bookings</th>
                          <th className="table-header text-right pr-8">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredPatients.length > 0 ? filteredPatients.map((patient) => {
                          const pcfg = getPlatformDisplay(patient.platform || 'whatsapp');
                          const PlatformIcon = pcfg.icon;

                          return (
                            <tr key={patient.id} className="premium-table-row group">
                              <td className="table-cell py-5">
                                <div className="flex items-center gap-3">
                                  <div className={`avatar ${pcfg.bgClass} text-white shadow-lg shadow-black/10 transition-transform group-hover:scale-110`}>
                                    {patient.name?.charAt(0) || 'P'}
                                  </div>
                                  <div>
                                    <p className="font-bold text-slate-800 text-base">
                                      {getPatientDisplayName(patient)}
                                    </p>
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">Verified Profile</p>
                                  </div>
                                </div>
                              </td>
                              <td className="table-cell">
                                <p className="text-sm font-semibold text-slate-700 font-mono break-all">{getPatientDisplayNumber(patient)}</p>
                              </td>
                              <td className="table-cell">
                                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-sm ${pcfg.badgeClass}`}>
                                  <PlatformIcon size={14} style={{ color: pcfg.color }} />
                                  <span className="text-xs font-bold uppercase tracking-wide">{pcfg.label}</span>
                                </div>
                              </td>
                              <td className="table-cell">
                                <div className="space-y-1">
                                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-tighter">External: {patient.external_id?.slice(-18) || '--'}</p>
                                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-tighter">Hospital: {patient.hospital_patient_id || '--'}</p>
                                </div>
                              </td>
                              <td className="table-cell">
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Joined: {patient.first_touch ? formatDate(patient.first_touch) : '--'}</p>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>
                                    <p className="text-xs font-bold text-slate-600">Active: {patient.last_touch ? formatDate(patient.last_touch) : '--'}</p>
                                  </div>
                                </div>
                              </td>
                              <td className="table-cell text-center">
                                <div className="inline-flex flex-col items-center justify-center w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 group-hover:bg-cyan-50 group-hover:border-cyan-100 transition-colors">
                                  <span className="text-lg font-black text-slate-800 group-hover:text-cyan-700">
                                    {(patient.total_appointments || 0) + (patient.total_diagnostics || 0) + (patient.total_admissions || 0)}
                                  </span>
                                  <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest -mt-1">Count</span>
                                </div>
                              </td>
                              <td className="table-cell text-right pr-8">
                                <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-all transform translate-x-2 group-hover:translate-x-0">
                                  <button
                                    onClick={() => fetchPatientDetail(patient)}
                                    className="p-2.5 rounded-xl bg-slate-50 text-slate-400 hover:text-cyan-600 hover:bg-cyan-50 transition-all shadow-sm border border-transparent hover:border-cyan-100"
                                    title="Patient File"
                                  >
                                    <Eye size={20} />
                                  </button>
                                  <button
                                    onClick={() => { setActiveTab('omnichannel'); fetchPatientDetail(patient); }}
                                    className="p-2.5 rounded-xl bg-slate-50 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-all shadow-sm border border-transparent hover:border-indigo-100"
                                    title="Secure Chat"
                                  >
                                    <MessageCircle size={20} />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        }) : (
                          <tr>
                            <td colSpan={7} className="table-cell text-center py-24">
                              <div className="bg-slate-50 w-24 h-24 rounded-3xl flex items-center justify-center mx-auto mb-6 rotate-12">
                                <Users size={48} className="text-slate-200 -rotate-12" />
                              </div>
                              <p className="text-slate-500 font-bold text-xl">No patients found</p>
                              <p className="text-sm text-slate-400 mt-2 max-w-xs mx-auto text-balance">The patient directory is currently empty. New patients will appear here as they interact with the hospital channels.</p>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}

              {/* APPOINTMENTS TAB */}
              {activeTab === 'appointments' && (
                <motion.div
                  key="appointments"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-6"
                >
                  {/* Filters: Status + Channel */}
                  <div className="flex flex-wrap items-center gap-4">
                    <div className="flex gap-2">
                      <span className="text-sm font-medium text-slate-500 self-center">Status:</span>
                      {['all', 'confirmed', 'completed', 'cancelled'].map((status) => (
                        <button
                          key={status}
                          onClick={() => setAppointmentFilter(status)}
                          className={`btn ${appointmentFilter === status ? 'btn-primary' : 'btn-secondary'}`}
                        >
                          {status.charAt(0).toUpperCase() + status.slice(1)}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <span className="text-sm font-medium text-slate-500 self-center">Date:</span>
                      {['all', 'today', 'yesterday', 'last7days'].map((d) => (
                        <button
                          key={d}
                          onClick={() => setAppointmentDateFilter(d)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${appointmentDateFilter === d ? 'bg-cyan-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                        >
                          {d === 'all' ? 'All Time' : d === 'last7days' ? 'Last 7 Days' : d.charAt(0).toUpperCase() + d.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-4">
                    <div className="flex gap-2">
                      <span className="text-sm font-medium text-slate-500 self-center">Doctor:</span>
                      <select
                        value={doctorFilter}
                        onChange={(e) => setDoctorFilter(e.target.value)}
                        className="input py-1.5 px-3 min-w-[200px]"
                      >
                        <option value="all">All Specialists</option>
                        {doctorList.map(doc => (
                          <option key={doc} value={doc}>{doc}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-sm font-medium text-slate-500 self-center">Channel:</span>
                      {['all', 'whatsapp', 'instagram', 'facebook'].map((src) => (
                        <button
                          key={src}
                          onClick={() => setAppointmentSourceFilter(src)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium ${appointmentSourceFilter === src ? 'bg-cyan-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                        >
                          {src === 'all' ? 'All' : getPlatformDisplay(src).label}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2 items-center">
                      <span className="text-sm font-medium text-slate-500 self-center">Sort:</span>
                      <select
                        value={appointmentSort}
                        onChange={(e) => setAppointmentSort(e.target.value as 'schedule_asc' | 'schedule_desc' | 'booked_newest' | 'booked_oldest')}
                        className="input py-1.5 px-3 min-w-[220px]"
                      >
                        <option value="schedule_asc">Schedule (Earliest first)</option>
                        <option value="schedule_desc">Schedule (Latest first)</option>
                        <option value="booked_newest">Booked Date (Newest first)</option>
                        <option value="booked_oldest">Booked Date (Oldest first)</option>
                      </select>
                    </div>
                  </div>

                  <div className="card p-5">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-bold text-slate-800">Front Desk Queue (Today Confirmed)</h4>
                      <button
                        type="button"
                        onClick={finalizeNextAppointment}
                        disabled={frontDeskQueue.length === 0}
                        className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <CheckCircle2 size={16} /> Finalize Next
                      </button>
                    </div>
                    {frontDeskQueue.length > 0 ? (
                      <div className="space-y-2 max-h-52 overflow-y-auto custom-scrollbar pr-1">
                        {frontDeskQueue.slice(0, 8).map((appt) => (
                          <div key={`queue-${appt.booking_id}`} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-50">
                            <div className="min-w-0">
                              <p className="font-semibold text-slate-800 truncate">{appt.patient_name}</p>
                              <p className="text-xs text-slate-500">{formatAppointmentDate(appt.date)} • {appt.time || '--'} • {appt.doctor || '--'}</p>
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => updateAppointmentStatus(appt.booking_id, 'completed')}
                                className="p-2 rounded-lg text-emerald-600 hover:bg-emerald-100 transition-colors"
                                title="Finalize Completed"
                              >
                                <CheckCircle2 size={16} />
                              </button>
                              <button
                                onClick={() => updateAppointmentStatus(appt.booking_id, 'no-show')}
                                className="p-2 rounded-lg text-amber-600 hover:bg-amber-100 transition-colors"
                                title="Mark No-show"
                              >
                                <AlertCircle size={16} />
                              </button>
                              <button
                                onClick={() => cancelAppointment(appt.booking_id)}
                                className="p-2 rounded-lg text-rose-600 hover:bg-rose-100 transition-colors"
                                title="Cancel"
                              >
                                <X size={16} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400">No confirmed appointments in today queue.</p>
                    )}
                  </div>

                  {/* Stats Row */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-cyan-100 text-cyan-600">
                        <Calendar size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{appointments.filter(a => a.status === 'confirmed').length}</p>
                        <p className="text-xs text-slate-500">Confirmed</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-emerald-100 text-emerald-600">
                        <CheckCircle2 size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{appointments.filter(a => a.status === 'completed').length}</p>
                        <p className="text-xs text-slate-500">Completed</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-rose-100 text-rose-600">
                        <X size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{appointments.filter(a => a.status === 'cancelled').length}</p>
                        <p className="text-xs text-slate-500">Cancelled</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-amber-100 text-amber-600">
                        <AlertCircle size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{appointments.filter(a => a.status === 'no-show').length}</p>
                        <p className="text-xs text-slate-500">No-show</p>
                      </div>
                    </div>
                  </div>

                  {/* Appointments Table */}
                  <div className="table-container shadow-2xl shadow-slate-200/50">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-100/50">
                          <th className="table-header text-left py-5">Patient Details</th>
                          <th className="table-header text-left">Patient ID</th>
                          <th className="table-header text-left">Channel</th>
                          <th className="table-header text-left">Specialist</th>
                          <th className="table-header text-left">Schedule</th>
                          <th className="table-header text-left">Booked At</th>
                          <th className="table-header text-center">Status</th>
                          <th className="table-header text-right pr-8">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredAppointments.length > 0 ? (
                          filteredAppointments
                            .map((appt) => {
                              const src = appt.source || 'whatsapp';
                              const pcfg = getPlatformDisplay(src);
                              const PlatformIcon = pcfg.icon;

                              return (
                                <tr key={appt.booking_id} className="premium-table-row group">
                                  <td className="table-cell py-5">
                                    <div className="flex items-center gap-3">
                                      <div className={`w-10 h-10 rounded-xl ${pcfg.bgClass} flex items-center justify-center text-white shadow-lg shadow-black/10`}>
                                        <Users size={20} />
                                      </div>
                                      <div>
                                        <p className="font-bold text-slate-800 text-base">{appt.patient_name}</p>
                                        <div className="flex items-center gap-2 mt-0.5">
                                          <span className="font-mono text-[10px] text-slate-400 uppercase tracking-tighter">ID: {appt.booking_id}</span>
                                          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                                          <span className="text-xs text-slate-500 font-medium">{appt.phone || '--'}</span>
                                        </div>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="table-cell">
                                    <span className="font-mono text-xs text-slate-600">
                                      {appt.patient_identifier || '--'}
                                    </span>
                                  </td>
                                  <td className="table-cell">
                                    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-sm ${pcfg.badgeClass} group-hover:scale-105 transition-transform`}>
                                      <PlatformIcon size={14} style={{ color: pcfg.color }} />
                                      <span className="text-xs font-bold uppercase tracking-wide">{pcfg.label}</span>
                                    </div>
                                  </td>
                                  <td className="table-cell">
                                    <div className="flex items-center gap-2 text-slate-700">
                                      <div className="p-1.5 rounded-lg bg-cyan-50 text-cyan-600">
                                        <Stethoscope size={14} />
                                      </div>
                                      <span className="font-medium">{appt.doctor || '--'}</span>
                                    </div>
                                  </td>
                                  <td className="table-cell">
                                    <div className="text-left">
                                      <p className="text-xs font-bold text-slate-800">Date: {formatAppointmentDate(appt.date)}</p>
                                      <p className="text-sm font-extrabold text-cyan-600">Time: {appt.time || '--'}</p>
                                    </div>
                                  </td>
                                  <td className="table-cell">
                                    <p className="text-xs font-semibold text-slate-700">{formatDateTime(appt.created_at)}</p>
                                    <p className="text-[10px] text-slate-400 font-medium">{formatRelativeTime(appt.created_at)}</p>
                                  </td>
                                  <td className="table-cell text-center">
                                    <span className={`badge ${getStatusBadge(appt.status)}`}>{appt.status}</span>
                                  </td>
                                  <td className="table-cell text-right pr-8">
                                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                      {appt.status.toLowerCase() === 'confirmed' && (
                                        <>
                                          <button
                                            onClick={() => updateAppointmentStatus(appt.booking_id, 'completed')}
                                            className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 hover:bg-emerald-600 hover:text-white transition-all shadow-sm"
                                            title="Complete"
                                          >
                                            <CheckCircle2 size={18} />
                                          </button>
                                          <button
                                            onClick={() => cancelAppointment(appt.booking_id)}
                                            className="p-2.5 rounded-xl bg-rose-50 text-rose-600 hover:bg-rose-600 hover:text-white transition-all shadow-sm"
                                            title="Cancel"
                                          >
                                            <X size={18} />
                                          </button>
                                        </>
                                      )}
                                      <button
                                        onClick={() => { setSelectedPatient(patients.find(p => p.phone === appt.phone || p.external_id === appt.user_id) || null); setShowPatientModal(true); }}
                                        className="p-2.5 rounded-xl bg-slate-50 text-slate-500 hover:bg-cyan-600 hover:text-white transition-all shadow-sm"
                                        title="View Patient"
                                      >
                                        <Eye size={18} />
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                              );
                            })
                        ) : (
                          <tr>
                            <td colSpan={8} className="table-cell text-center py-24">
                              <div className="bg-slate-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Calendar size={40} className="text-slate-200" />
                              </div>
                              <p className="text-slate-500 font-bold text-lg">No appointments scheduled</p>
                              <p className="text-sm text-slate-400 mt-1 max-w-xs mx-auto">Try adjusting your filters or checking different appointment channels.</p>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}

              {/* CALENDAR TAB */}
              {activeTab === 'calendar' && (
                <motion.div
                  key="calendar"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 card p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold text-slate-800">
                          {calendarMonth.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}
                        </h3>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1))}
                            className="btn btn-ghost"
                          >
                            Previous
                          </button>
                          <button
                            type="button"
                            onClick={() => setCalendarMonth(new Date())}
                            className="btn btn-secondary"
                          >
                            Today
                          </button>
                          <button
                            type="button"
                            onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1))}
                            className="btn btn-ghost"
                          >
                            Next
                          </button>
                        </div>
                      </div>
                      <div className="grid grid-cols-7 gap-1 text-center text-sm">
                        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                          <div key={d} className="font-semibold text-slate-500 py-1">{d}</div>
                        ))}
                        {Array.from({ length: new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1).getDay() }, (_, i) => (
                          <div key={`pad-${i}`} />
                        ))}
                        {Array.from({ length: new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0).getDate() }, (_, i) => i + 1).map((day) => {
                          const dateStr = `${calendarMonth.getFullYear()}-${String(calendarMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                          const count = appointments.filter((a) => a.date === dateStr && a.status === 'confirmed').length;
                          const isSelected = calendarSelectedDate === dateStr;
                          return (
                            <button
                              key={day}
                              type="button"
                              onClick={() => setCalendarSelectedDate(dateStr)}
                              className={`p-2 rounded-lg text-sm transition-colors ${isSelected ? 'bg-cyan-600 text-white' : count > 0 ? 'bg-cyan-50 text-cyan-700 hover:bg-cyan-100' : 'hover:bg-slate-100 text-slate-700'
                                }`}
                            >
                              {day}
                              {count > 0 && <span className="block text-[10px] opacity-80">{count}</span>}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <div className="card p-6">
                      <h3 className="font-bold text-slate-800 mb-4">
                        {calendarSelectedDate
                          ? new Date(calendarSelectedDate + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })
                          : 'Select a date'}
                      </h3>
                      <div className="space-y-2 max-h-[320px] overflow-y-auto">
                        {calendarSelectedDate
                          ? appointments
                            .filter((a) => a.date === calendarSelectedDate)
                            .map((a) => (
                              <div key={a.booking_id} className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                                <p className="font-semibold text-slate-800">{a.patient_name}</p>
                                <p className="text-xs text-slate-500">{a.doctor} â€¢ {a.time}</p>
                                <span className={`badge mt-1 ${getStatusBadge(a.status)}`}>{a.status}</span>
                              </div>
                            ))
                          : null}
                        {calendarSelectedDate && appointments.filter((a) => a.date === calendarSelectedDate).length === 0 && (
                          <p className="text-slate-400 text-sm">No appointments on this day.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* DIAGNOSTICS TAB */}
              {activeTab === 'diagnostics' && (
                <motion.div
                  key="diagnostics"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-6"
                >
                  {/* Stats Row */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-emerald-100 text-emerald-600">
                        <TestTube size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{diagnostics.filter(d => d.status === 'confirmed').length}</p>
                        <p className="text-xs text-slate-500">Confirmed</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-cyan-100 text-cyan-600">
                        <CheckCircle2 size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{diagnostics.filter(d => d.status === 'completed').length}</p>
                        <p className="text-xs text-slate-500">Completed</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-rose-100 text-rose-600">
                        <X size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{diagnostics.filter(d => d.status === 'cancelled').length}</p>
                        <p className="text-xs text-slate-500">Cancelled</p>
                      </div>
                    </div>
                  </div>

                  {/* Diagnostics Table */}
                  <div className="table-container">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-100">
                          <th className="table-header text-left">Booking ID</th>
                          <th className="table-header text-left">Patient</th>
                          <th className="table-header text-left">Phone</th>
                          <th className="table-header text-left">Test Type</th>
                          <th className="table-header text-left">Date & Time</th>
                          <th className="table-header text-center">Status</th>
                          <th className="table-header text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {diagnostics.length > 0 ? diagnostics.map((diag) => (
                          <tr key={diag.booking_id} className="table-row">
                            <td className="table-cell">
                              <span className="font-mono text-xs bg-emerald-100 px-2 py-1 rounded">{diag.booking_id}</span>
                            </td>
                            <td className="table-cell">
                              <p className="font-semibold text-slate-800">{diag.patient_name}</p>
                              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Booked: {formatDate(diag.created_at)}</p>
                            </td>
                            <td className="table-cell text-slate-600">{diag.phone || '--'}</td>
                            <td className="table-cell">
                              <span className="flex items-center gap-2 text-slate-600">
                                <TestTube size={16} />
                                {diag.test_type}
                              </span>
                            </td>
                            <td className="table-cell">
                              <div>
                                <p className="font-medium text-slate-800">{diag.date || '--'}</p>
                                <p className="text-xs text-slate-500">{diag.time || '--'}</p>
                              </div>
                            </td>
                            <td className="table-cell text-center">
                              <span className={`badge ${getStatusBadge(diag.status)}`}>{diag.status}</span>
                            </td>
                            <td className="table-cell text-right">
                              <div className="flex items-center justify-end gap-1">
                                {diag.status === 'confirmed' && (
                                  <>
                                    <button
                                      onClick={() => updateDiagnosticStatus(diag.booking_id, 'completed')}
                                      className="p-2 rounded-lg text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                                      title="Mark Complete"
                                    >
                                      <CheckCircle2 size={18} />
                                    </button>
                                    <button
                                      onClick={() => updateDiagnosticStatus(diag.booking_id, 'cancelled')}
                                      className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                                      title="Cancel"
                                    >
                                      <X size={18} />
                                    </button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        )) : (
                          <tr>
                            <td colSpan={7} className="table-cell text-center py-16">
                              <TestTube size={48} className="mx-auto text-slate-200 mb-4" />
                              <p className="text-slate-400 font-medium">No diagnostic bookings found</p>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}

              {/* ADMISSIONS TAB */}
              {activeTab === 'admissions' && (
                <motion.div
                  key="admissions"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-6"
                >
                  {/* Stats Row */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-amber-100 text-amber-600">
                        <Clock size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{admissions.filter(a => a.status === 'pending').length}</p>
                        <p className="text-xs text-slate-500">Pending</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-emerald-100 text-emerald-600">
                        <CheckCircle2 size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{admissions.filter(a => a.status === 'confirmed').length}</p>
                        <p className="text-xs text-slate-500">Confirmed</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-cyan-100 text-cyan-600">
                        <Bed size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{admissions.filter(a => a.status === 'admitted').length}</p>
                        <p className="text-xs text-slate-500">Admitted</p>
                      </div>
                    </div>
                    <div className="card p-4 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-rose-100 text-rose-600">
                        <X size={24} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{admissions.filter(a => a.status === 'cancelled').length}</p>
                        <p className="text-xs text-slate-500">Cancelled</p>
                      </div>
                    </div>
                  </div>

                  {/* Admissions Table */}
                  <div className="table-container">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-100">
                          <th className="table-header text-left">Admission ID</th>
                          <th className="table-header text-left">Patient</th>
                          <th className="table-header text-left">Phone</th>
                          <th className="table-header text-left">Type</th>
                          <th className="table-header text-left">Age/Gender</th>
                          <th className="table-header text-left">Preferred Date</th>
                          <th className="table-header text-center">Status</th>
                          <th className="table-header text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {admissions.length > 0 ? admissions.map((adm) => (
                          <tr key={adm.admission_id} className="table-row">
                            <td className="table-cell">
                              <span className="font-mono text-xs bg-amber-100 px-2 py-1 rounded">{adm.admission_id}</span>
                            </td>
                            <td className="table-cell py-4">
                              <p className="font-semibold text-slate-800">{adm.patient_name}</p>
                              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Booked: {formatDate(adm.created_at)}</p>
                            </td>
                            <td className="table-cell text-slate-600">{adm.phone || '--'}</td>
                            <td className="table-cell">
                              <span className={`badge ${adm.admission_type === 'Emergency' ? 'badge-danger' : 'badge-info'}`}>
                                {adm.admission_type}
                              </span>
                            </td>
                            <td className="table-cell text-slate-600">
                              {adm.age ? `${adm.age} yrs` : '--'} / {adm.sex || '--'}
                            </td>
                            <td className="table-cell text-slate-600">{adm.preferred_date || '--'}</td>
                            <td className="table-cell text-center">
                              <span className={`badge ${getStatusBadge(adm.status)}`}>{adm.status}</span>
                            </td>
                            <td className="table-cell text-right">
                              <div className="flex items-center justify-end gap-1">
                                {adm.status === 'pending' && (
                                  <>
                                    <button
                                      onClick={() => updateAdmissionStatus(adm.admission_id, 'confirmed')}
                                      className="p-2 rounded-lg text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                                      title="Confirm"
                                    >
                                      <CheckCircle2 size={18} />
                                    </button>
                                    <button
                                      onClick={() => updateAdmissionStatus(adm.admission_id, 'cancelled')}
                                      className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                                      title="Cancel"
                                    >
                                      <X size={18} />
                                    </button>
                                  </>
                                )}
                                {adm.status === 'confirmed' && (
                                  <button
                                    onClick={() => updateAdmissionStatus(adm.admission_id, 'admitted')}
                                    className="p-2 rounded-lg text-slate-400 hover:text-cyan-600 hover:bg-cyan-50 transition-colors"
                                    title="Mark Admitted"
                                  >
                                    <Bed size={18} />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        )) : (
                          <tr>
                            <td colSpan={8} className="table-cell text-center py-16">
                              <Bed size={48} className="mx-auto text-slate-200 mb-4" />
                              <p className="text-slate-400 font-medium">No admission requests found</p>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}

              {/* OMNICHANNEL TAB */}
              {activeTab === 'omnichannel' && (
                <motion.div
                  key="omnichannel"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="grid grid-cols-3 gap-6 h-[calc(100vh-200px)]"
                >
                  {/* Conversations List */}
                  <div className="card flex flex-col min-h-0">
                    <div className="flex-shrink-0 p-4 border-b border-slate-100">
                      <h3 className="font-bold text-slate-800">Recent Conversations</h3>
                    </div>
                    <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                      {patients.slice(0, 15).map((patient) => (
                        <div
                          key={patient.id}
                          onClick={() => fetchPatientDetail(patient)}
                          className={`p-4 border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors ${selectedPatient?.id === patient.id ? 'bg-cyan-50 border-l-2 border-l-cyan-500' : ''}`}
                        >
                          <div className="flex items-center gap-3">
                            <div className="avatar bg-cyan-100 text-cyan-600 relative">
                              {patient.name?.charAt(0) || 'P'}
                              <span className={`absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-white ${getPlatformDisplay(patient.platform || 'whatsapp').bgClass}`}></span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-slate-800 truncate">{getPatientDisplayName(patient)}</p>
                              <p className="text-xs mt-0.5">
                                <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${getPlatformDisplay(patient.platform || 'whatsapp').className}`}>
                                  {getPlatformDisplay(patient.platform || 'whatsapp').short}
                                </span>
                              </p>
                              <p className="text-xs text-slate-500 font-mono break-all mt-1">{getPatientDisplayNumber(patient)}</p>
                            </div>
                            <span className="text-xs text-slate-400">{patient.last_touch ? formatTime(patient.last_touch) : ''}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Chat Area - fixed height so messages scroll inside */}
                  <div className="col-span-2 card flex flex-col min-h-0">
                    {selectedPatient ? (
                      <>
                        {/* Chat Header */}
                        <div className="flex-shrink-0 p-4 border-b border-slate-100 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="avatar bg-cyan-100 text-cyan-600">
                              {selectedPatient.name?.charAt(0) || 'P'}
                            </div>
                            <div>
                              <p className="font-semibold text-slate-800">{getPatientDisplayName(selectedPatient)}</p>
                              <p className="text-xs flex items-center gap-1.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${getPlatformDisplay(selectedPatient.platform || 'whatsapp').bgClass}`}></span>
                                <span className="font-medium text-slate-600">{getPlatformDisplay(selectedPatient.platform || 'whatsapp').label}</span>
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={togglePatientAutomation}
                              disabled={updatingAutomation}
                              className={`btn ${isAutomationPaused(selectedPatient) ? 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100' : 'btn-secondary'} disabled:opacity-60`}
                              title={isAutomationPaused(selectedPatient) ? 'Resume automation for this patient' : 'Pause automation for this patient'}
                            >
                              <span className={`w-2 h-2 rounded-full ${isAutomationPaused(selectedPatient) ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
                              {isAutomationPaused(selectedPatient) ? 'Automation Paused' : 'Automation Active'}
                            </button>
                            <button className="btn btn-ghost" title="Call"><Phone size={18} /></button>
                          </div>
                        </div>

                        {/* Messages - scrollable, latest at bottom */}
                        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                          <div className="flex-1 min-h-0 p-4 overflow-y-auto custom-scrollbar space-y-4">
                            {patientTimeline.length > 0 ? (
                              <>
                                {patientTimeline.slice().reverse().map((msg, idx) => {
                                  const { text, options } = formatMessageForDisplay(msg.message || '');
                                  return (
                                    <div key={idx} className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
                                      <div className={`chat-bubble ${msg.direction} max-w-[85%]`}>
                                        {text && <p className="whitespace-pre-line break-words">{text}</p>}
                                        {options && options.length > 0 && (
                                          <div className="mt-2 flex flex-wrap gap-1.5">
                                            {options.map((opt, i) => (
                                              <span key={i} className="inline-flex items-center px-2.5 py-1 rounded-lg bg-white/20 text-sm">
                                                {opt}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                        <p className={`text-xs mt-2 ${msg.direction === 'outbound' ? 'text-cyan-100' : 'text-slate-400'}`}>
                                          {formatTime(msg.timestamp)}
                                        </p>
                                      </div>
                                    </div>
                                  );
                                })}
                                <div ref={chatMessagesEndRef} />
                              </>
                            ) : (
                              <div className="text-center py-16 text-slate-400">
                                <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
                                <p>No messages yet</p>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Message Input */}
                        <div className="flex-shrink-0 p-4 border-t border-slate-100">
                          <div className="flex gap-3">
                            <input
                              type="text"
                              value={whatsappMessageInput}
                              onChange={(e) => setWhatsappMessageInput(e.target.value)}
                              onKeyDown={(e) => e.key === 'Enter' && sendWhatsAppMessage()}
                              placeholder="Type a message to send..."
                              className="input flex-1"
                            />
                            <button
                              type="button"
                              onClick={sendWhatsAppMessage}
                              disabled={sendingMessage || !whatsappMessageInput.trim()}
                              className="btn btn-primary"
                            >
                              <Send size={18} />
                            </button>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="flex-1 flex items-center justify-center">
                        <div className="text-center text-slate-400">
                          <MessageSquare size={64} className="mx-auto mb-4 opacity-30" />
                          <p className="font-medium">Select a conversation</p>
                          <p className="text-sm">Choose a patient from the list to view messages</p>
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </div>
      </main>

      {/* Patient Detail Modal */}
      <AnimatePresence>
        {showPatientModal && selectedPatient && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
            onClick={() => setShowPatientModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-cyan-100 text-cyan-600 flex items-center justify-center text-2xl font-bold">
                    {selectedPatient.name?.charAt(0) || 'P'}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-800">{selectedPatient.name || 'Anonymous Patient'}</h2>
                    <p className="text-slate-500 flex items-center gap-2">
                      {selectedPatient.phone || selectedPatient.external_id}
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${getPlatformDisplay(selectedPatient.platform || 'whatsapp').className}`}>
                        {getPlatformDisplay(selectedPatient.platform || 'whatsapp').label}
                      </span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowPatientModal(false)}
                  className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="p-6 border-b border-slate-100 bg-slate-50/70">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Hospital Patient ID</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={hospitalPatientIdInput}
                    onChange={(e) => setHospitalPatientIdInput(e.target.value)}
                    placeholder="Enter patient ID from your hospital system"
                    className="input flex-1"
                  />
                  <button
                    type="button"
                    onClick={saveHospitalPatientId}
                    disabled={savingHospitalPatientId || !hospitalPatientIdInput.trim()}
                    className="btn btn-primary"
                  >
                    {savingHospitalPatientId ? 'Saving...' : 'Save ID'}
                  </button>
                </div>
              </div>

              <div className="p-6 grid grid-cols-4 gap-4 border-b border-slate-100">
                <div className="text-center p-4 bg-slate-50 rounded-xl">
                  <p className="text-2xl font-bold text-cyan-600">{selectedPatient.total_appointments || 0}</p>
                  <p className="text-xs text-slate-500 font-medium">Appointments</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-xl">
                  <p className="text-2xl font-bold text-emerald-600">{selectedPatient.total_diagnostics || 0}</p>
                  <p className="text-xs text-slate-500 font-medium">Diagnostics</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-xl">
                  <p className="text-2xl font-bold text-amber-600">{selectedPatient.total_admissions || 0}</p>
                  <p className="text-xs text-slate-500 font-medium">Admissions</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-xl">
                  <p className="text-sm font-bold text-slate-700">{selectedPatient.first_touch ? formatDate(selectedPatient.first_touch) : '--'}</p>
                  <p className="text-xs text-slate-500 font-medium">First Contact</p>
                </div>
              </div>

              <div className="p-6 max-h-80 overflow-y-auto custom-scrollbar">
                <h3 className="font-semibold text-slate-800 mb-4">Recent Activity</h3>
                <div className="space-y-3">
                  {patientTimeline.slice(0, 10).map((item, idx) => {
                    const { text, options } = formatMessageForDisplay(item.message || '');
                    return (
                      <div key={idx} className="flex items-start gap-3 p-3 rounded-xl bg-slate-50">
                        <div className={`p-2 rounded-lg ${item.direction === 'inbound' ? 'bg-cyan-100 text-cyan-600' : 'bg-emerald-100 text-emerald-600'}`}>
                          {item.direction === 'inbound' ? <MessageCircle size={14} /> : <Send size={14} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-slate-700 whitespace-pre-line break-words">{text}</p>
                          {options && options.length > 0 && (
                            <p className="text-xs text-slate-500 mt-0.5">Options: {options.join(', ')}</p>
                          )}
                          <p className="text-xs text-slate-400 mt-1">{formatDate(item.timestamp)} at {formatTime(item.timestamp)}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Real-time Toast Notifications */}
      <div className="fixed top-24 right-8 z-[100] flex flex-col gap-3 w-80 pointer-events-none">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 50, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.9 }}
              className="bg-white/90 backdrop-blur-xl border border-white/20 p-4 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.15)] flex gap-4 pointer-events-auto cursor-pointer group"
              onClick={() => {
                setToasts(prev => prev.filter(t => t.id !== toast.id));
                if (toast.type === 'appointment') setActiveTab('appointments');
                if (toast.type === 'diagnostic') setActiveTab('diagnostics');
                if (toast.type === 'admission') setActiveTab('admissions');
              }}
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${toast.type === 'appointment' ? 'bg-cyan-500 text-white' :
                toast.type === 'diagnostic' ? 'bg-emerald-500 text-white' :
                  'bg-amber-500 text-white'
                }`}>
                {toast.type === 'appointment' && <Calendar size={20} />}
                {toast.type === 'diagnostic' && <TestTube size={20} />}
                {toast.type === 'admission' && <Bed size={20} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex justify-between items-start">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{toast.title}</p>
                  <span className="text-[10px] font-bold text-slate-300 group-hover:text-slate-500 transition-colors">JUST NOW</span>
                </div>
                <p className="text-sm font-bold text-slate-800 mt-1 truncate">{toast.patientName}</p>
                <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{toast.message}</p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setToasts(prev => prev.filter(t => t.id !== toast.id));
                }}
                className="self-start text-slate-300 hover:text-slate-500 transition-colors"
              >
                <X size={14} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default App;




