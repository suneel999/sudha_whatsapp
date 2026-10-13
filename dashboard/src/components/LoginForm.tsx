import React, { useState } from 'react';
import axios from 'axios';
import { Lock, User, Building2, AlertCircle, RefreshCcw } from 'lucide-react';
import { motion } from 'framer-motion';

interface LoginFormProps {
    onLoginSuccess: (token: string, user: any) => void;
    apiBase: string;
}

const LoginForm: React.FC<LoginFormProps> = ({ onLoginSuccess, apiBase }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username || !password) return;

        setLoading(true);
        setError(null);

        try {
            const response = await axios.post(`${apiBase}/api/auth/login`, {
                username,
                password
            });

            if (response.data.success) {
                onLoginSuccess(response.data.token, response.data.user);
            }
        } catch (err: any) {
            console.error('Login error:', err);
            setError(err.response?.data?.error || 'Failed to authenticate. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="max-w-md w-full"
            >
                <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/60 overflow-hidden border border-slate-100">
                    <div className="sidebar-gradient p-8 text-white text-center">
                        <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur mx-auto mb-4">
                            <Building2 size={36} />
                        </div>
                        <h1 className="text-2xl font-bold tracking-tight">Sudha CRM</h1>
                        <p className="text-cyan-100 font-medium">Hospital Secure Access</p>
                    </div>

                    <div className="p-8">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {error && (
                                <div className="bg-rose-50 border border-rose-100 text-rose-600 px-4 py-3 rounded-xl flex items-center gap-3 text-sm animate-shake">
                                    <AlertCircle size={18} />
                                    <span>{error}</span>
                                </div>
                            )}

                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider ml-1">Username</label>
                                <div className="relative">
                                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                    <input
                                        type="text"
                                        required
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 outline-none transition-all text-slate-700 font-medium"
                                        placeholder="Enter your username"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider ml-1">Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                    <input
                                        type="password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 outline-none transition-all text-slate-700 font-medium"
                                        placeholder="••••••••"
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full sidebar-gradient text-white font-bold py-4 rounded-xl shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 group disabled:opacity-70 disabled:hover:scale-100"
                            >
                                {loading ? (
                                    <RefreshCcw className="animate-spin" size={20} />
                                ) : (
                                    <>
                                        Sign In
                                        <Lock size={18} className="opacity-50 group-hover:opacity-100 transition-opacity" />
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="mt-8 pt-8 border-t border-slate-50 text-center">
                            <p className="text-sm text-slate-400">
                                Unauthorized access is strictly prohibited.
                            </p>
                        </div>
                    </div>
                </div>

                <p className="text-center mt-6 text-slate-400 text-xs">
                    &copy; {new Date().getFullYear()} Sudha Hospital. All rights reserved.
                </p>
            </motion.div>
        </div>
    );
};

export default LoginForm;
