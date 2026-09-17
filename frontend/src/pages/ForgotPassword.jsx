import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  Mail,
  Moon,
  Navigation,
  Shield,
  ShieldCheck,
  Sun,
  Zap,
} from 'lucide-react';
import { forgotPassword, resetPassword } from '../api_services';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isResetComplete, setIsResetComplete] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  // Theme State (synced with localStorage)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    try {
      const saved = localStorage.getItem('roadsense_theme');
      return saved !== null ? saved === 'dark' : true;
    } catch {
      return true;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('roadsense_theme', isDarkMode ? 'dark' : 'light');
    } catch { }
  }, [isDarkMode]);

  async function requestOtp(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    setIsSending(true);
    try {
      const response = await forgotPassword(email);
      setMessage(response?.message || 'A reset code has been sent to your email.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Unable to send the reset code.');
    } finally {
      setIsSending(false);
    }
  }

  async function handleResetPassword(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    setIsResetting(true);
    try {
      const response = await resetPassword({
        email,
        otp,
        newPassword,
      });
      setMessage(response?.message || 'Password reset successful.');
      setIsResetComplete(true);
      setOtp('');
      setNewPassword('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Unable to reset the password.');
    } finally {
      setIsResetting(false);
    }
  }

  // Theme styling tokens consistent with Login and Register
  const theme = {
    root: isDarkMode
      ? 'bg-[#0A0D12] text-asphalt-100'
      : 'bg-[#F8FAFC] text-slate-800',
    header: isDarkMode
      ? 'bg-[#0A0D12]/90 border-white/[0.08]'
      : 'bg-white/90 border-slate-200/90 shadow-sm',
    brandText: isDarkMode ? 'text-white' : 'text-slate-900',
    brandSub: isDarkMode ? 'text-asphalt-400' : 'text-slate-500',
    backBtn: isDarkMode
      ? 'border-white/[0.1] bg-white/[0.03] hover:bg-white/[0.06] text-asphalt-300 hover:text-white'
      : 'border-slate-200 bg-slate-100/80 hover:bg-slate-200/80 text-slate-600 hover:text-slate-900',
    toggleBtn: isDarkMode
      ? 'border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08] text-asphalt-200'
      : 'border-slate-200 bg-slate-100 hover:bg-slate-200/80 text-slate-700',
    badge: isDarkMode
      ? 'bg-asphalt-900/90 border-white/[0.12] text-asphalt-200 shadow-black/60'
      : 'bg-white border-slate-200 text-slate-700 shadow-slate-200/60 shadow-md',
    card: isDarkMode
      ? 'bg-asphalt-900/90 border-white/[0.1] shadow-2xl shadow-black/80'
      : 'bg-white border-slate-200 shadow-2xl shadow-slate-200/60',
    infoCard: isDarkMode
      ? 'bg-asphalt-900/60 border-white/[0.08] hover:border-signal-blue/40'
      : 'bg-white border-slate-200/90 hover:border-signal-blue/50 shadow-sm',
    heading: isDarkMode ? 'text-white' : 'text-slate-900',
    subtext: isDarkMode ? 'text-asphalt-300' : 'text-slate-600',
    muted: isDarkMode ? 'text-asphalt-400' : 'text-slate-500',
    label: isDarkMode ? 'text-asphalt-300' : 'text-slate-700',
    input: isDarkMode
      ? 'bg-asphalt-950 border-white/[0.1] text-white focus:border-signal-blue placeholder:text-asphalt-500'
      : 'bg-slate-50 border-slate-200 text-slate-900 focus:bg-white focus:border-signal-blue placeholder:text-slate-400',
    border: isDarkMode ? 'border-white/[0.08]' : 'border-slate-200',
    link: isDarkMode ? 'text-signal-blue hover:text-sky-300' : 'text-signal-blue hover:text-blue-700',
  };

  return (
    <div
      className={`min-h-screen ${theme.root} selection:bg-signal-blue selection:text-white font-sans overflow-x-hidden antialiased transition-colors duration-300 flex flex-col justify-between`}
    >
      {/* ========================================================================= */}
      {/* 1. HIGH-TECH BLUEPRINT & GEOMETRIC GRID BACKGROUND                        */}
      {/* ========================================================================= */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div
          className={`absolute -top-40 left-1/2 -translate-x-1/2 w-[1200px] h-[700px] blur-[160px] rounded-full transition-colors duration-500 ${isDarkMode
            ? 'bg-gradient-to-b from-signal-blue/25 via-signal-blue/8 to-transparent'
            : 'bg-gradient-to-b from-sky-200/50 via-blue-100/20 to-transparent'
            }`}
        />
        <div
          className={`absolute top-[30%] -left-80 w-[750px] h-[750px] blur-[180px] rounded-full transition-colors duration-500 ${isDarkMode ? 'bg-cyan-500/10' : 'bg-sky-400/10'
            }`}
        />
        <div
          className={`absolute top-[55%] -right-80 w-[750px] h-[750px] blur-[180px] rounded-full transition-colors duration-500 ${isDarkMode ? 'bg-signal-green/10' : 'bg-emerald-400/10'
            }`}
        />

        {/* 48px Engineering Grid Lines */}
        <div
          className={`absolute inset-0 transition-opacity duration-500 ${isDarkMode ? 'opacity-[0.06]' : 'opacity-[0.08]'
            }`}
          style={{
            backgroundImage: `linear-gradient(to right, ${isDarkMode ? '#EDEFF1' : '#64748B'
              } 1px, transparent 1px), linear-gradient(to bottom, ${isDarkMode ? '#EDEFF1' : '#64748B'
              } 1px, transparent 1px)`,
            backgroundSize: '48px 48px',
            maskImage: 'radial-gradient(ellipse at center, black 70%, transparent 100%)',
            WebkitMaskImage: 'radial-gradient(ellipse at center, black 70%, transparent 100%)',
          }}
        />

        {/* 96px Intersection Markers */}
        <div
          className={`absolute inset-0 transition-opacity duration-500 ${isDarkMode ? 'opacity-[0.08]' : 'opacity-[0.1]'
            }`}
          style={{
            backgroundImage: `radial-gradient(circle, ${isDarkMode ? '#3E7CB1' : '#2563EB'
              } 1.5px, transparent 1.5px)`,
            backgroundSize: '96px 96px',
            maskImage: 'radial-gradient(ellipse at center, black 65%, transparent 100%)',
            WebkitMaskImage: 'radial-gradient(ellipse at center, black 65%, transparent 100%)',
          }}
        />

        <div
          className={`absolute top-20 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent ${isDarkMode ? 'via-white/[0.08]' : 'via-slate-200'
            } to-transparent`}
        />
      </div>

      {/* ========================================================================= */}
      {/* 2. FIXED AUTH HEADER                                                      */}
      {/* ========================================================================= */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 w-full backdrop-blur-2xl border-b transition-colors duration-300 ${theme.header}`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3.5 flex-shrink-0 group">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-signal-blue via-signal-blue to-signal-blue/40 border border-white/25 shadow-xl shadow-signal-blue/30 group-hover:scale-105 transition-transform">
              <Navigation size={22} className="text-white transform -rotate-45" />
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-signal-green opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-signal-green" />
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-xl font-black tracking-tight transition-colors ${theme.brandText}`}>
                  RoadSense
                </span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-signal-blue/20 text-signal-blue border border-signal-blue/40 tracking-wider">
                  AI
                </span>
              </div>
              <p className={`text-[10px] tracking-wider font-mono uppercase transition-colors ${theme.brandSub}`}>
                Smart Traffic &amp; Safety
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsDarkMode((prev) => !prev)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-mono transition-all shadow-sm group ${theme.toggleBtn}`}
              aria-label="Toggle theme display mode"
              title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {isDarkMode ? (
                <Sun size={15} className="text-amber-400 group-hover:rotate-45 transition-transform" />
              ) : (
                <Moon size={15} className="text-signal-blue group-hover:-rotate-12 transition-transform" />
              )}
              <span className="text-[11px] font-semibold hidden sm:inline">
                {isDarkMode ? 'Dark' : 'Light'}
              </span>
            </button>

            <Link
              to="/login"
              className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition-colors ${isDarkMode ? 'text-asphalt-300 hover:text-white hover:bg-white/[0.06]' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
            >
              Sign In
            </Link>
          </div>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* 3. SPLIT GRID CONTENT: RECOVERY STEPS + PASSWORD RESET CARD               */}
      {/* ========================================================================= */}
      <main className="relative z-10 flex-grow flex items-center justify-center pt-28 pb-16 md:pt-36 md:pb-20 px-4 sm:px-6">
        <div className="max-w-6xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left Column: Security Recovery Steps (Visible on lg, prevents looking plain) */}
          <motion.div
            initial={{ opacity: 0, x: -25 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-6 space-y-6 hidden lg:block"
          >
            {/* Back Navigation Arrow + Title Side-by-Side */}
            <div className="flex items-start gap-3.5 sm:gap-4">
              <Link
                to="/"
                className={`inline-flex items-center justify-center w-11 h-11 rounded-2xl border transition-all duration-200 hover:-translate-x-1 shadow-sm shrink-0 mt-1 group ${
                  isDarkMode
                    ? 'border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08] text-asphalt-200 hover:text-white shadow-black/40'
                    : 'border-slate-200 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 shadow-slate-200/60'
                }`}
                aria-label="Back to Overview"
                title="Back to Overview"
              >
                <ArrowLeft size={20} className="transition-transform group-hover:-translate-x-0.5" />
              </Link>

              <h1 className={`text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight leading-[1.1] ${theme.heading}`}>
                Secure Credential{' '}
                <span className="bg-gradient-to-r from-sky-400 via-cyan-400 to-signal-green bg-clip-text text-transparent">
                  Recovery.
                </span>
              </h1>
            </div>

            <p className={`text-base leading-relaxed ${theme.subtext}`}>
              Follow our two-factor verification protocol to safely reset your credentials and restore command center access.
            </p>

            {/* 4 Feature / Step Cards */}
            <div className="grid grid-cols-2 gap-3.5 pt-2">
              <div className={`p-4 rounded-2xl border transition-all ${theme.infoCard}`}>
                <div className="w-8 h-8 rounded-xl bg-signal-blue/15 text-signal-blue flex items-center justify-center mb-2.5">
                  <Mail size={17} />
                </div>
                <h4 className={`text-xs font-bold ${theme.heading}`}>1. Identity Dispatch</h4>
                <p className={`text-[11px] mt-1 leading-relaxed ${theme.muted}`}>
                  A 6-digit security code is sent to your agency email.
                </p>
              </div>

              <div className={`p-4 rounded-2xl border transition-all ${theme.infoCard}`}>
                <div className="w-8 h-8 rounded-xl bg-signal-green/15 text-signal-green flex items-center justify-center mb-2.5">
                  <KeyRound size={17} />
                </div>
                <h4 className={`text-xs font-bold ${theme.heading}`}>2. One-Time Verification</h4>
                <p className={`text-[11px] mt-1 leading-relaxed ${theme.muted}`}>
                  Codes are strictly validated and time-limited for security.
                </p>
              </div>

              <div className={`p-4 rounded-2xl border transition-all ${theme.infoCard}`}>
                <div className="w-8 h-8 rounded-xl bg-signal-amber/15 text-signal-amber flex items-center justify-center mb-2.5">
                  <Lock size={17} />
                </div>
                <h4 className={`text-xs font-bold ${theme.heading}`}>3. Secure Password</h4>
                <p className={`text-[11px] mt-1 leading-relaxed ${theme.muted}`}>
                  Create a new password with minimum 6 characters.
                </p>
              </div>

              <div className={`p-4 rounded-2xl border transition-all ${theme.infoCard}`}>
                <div className="w-8 h-8 rounded-xl bg-signal-blue/15 text-signal-blue flex items-center justify-center mb-2.5">
                  <ShieldCheck size={17} />
                </div>
                <h4 className={`text-xs font-bold ${theme.heading}`}>4. Audit Logged</h4>
                <p className={`text-[11px] mt-1 leading-relaxed ${theme.muted}`}>
                  Reset actions are timestamped in system audit logs.
                </p>
              </div>
            </div>

            {/* Assistance Banner */}
            <div className={`flex items-center gap-3 p-3.5 rounded-2xl border text-xs font-mono ${theme.infoCard}`}>
              <Shield size={16} className="text-signal-blue shrink-0" />
              <span className={theme.subtext}>
                Need immediate access? Contact support at{' '}
                <span className="text-signal-blue font-bold">support@roadsense.ai</span>
              </span>
            </div>
          </motion.div>

          {/* Right Column: Password Reset Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-6 w-full max-w-md mx-auto"
          >
            {/* Mobile Header (Shown on small screens) */}
            <div className="text-center mb-6 lg:hidden relative">
              <Link
                to="/"
                className={`absolute left-0 top-0 inline-flex items-center justify-center w-9 h-9 rounded-xl border transition-all ${
                  isDarkMode
                    ? 'border-white/[0.12] bg-white/[0.04] text-asphalt-200 hover:text-white'
                    : 'border-slate-200 bg-white text-slate-600 hover:text-slate-900 shadow-sm'
                }`}
                aria-label="Back to Overview"
                title="Back to Overview"
              >
                <ArrowLeft size={16} />
              </Link>
              <h2 className={`text-2xl font-black tracking-tight ${theme.heading}`}>
                Reset Account Password
              </h2>
              <p className={`mt-1 text-xs ${theme.subtext}`}>
                Request a verification code, then choose a new password.
              </p>
            </div>

            <div className={`rounded-3xl border p-6 sm:p-8 backdrop-blur-xl transition-colors duration-300 ${theme.card}`}>
              <div className="hidden lg:block mb-5 pb-3 border-b border-white/[0.08]">
                <h2 className={`text-xl font-bold tracking-tight ${theme.heading}`}>
                  Reset Password
                </h2>
                <p className={`mt-1 text-xs ${theme.subtext}`}>
                  Request a verification code, then set your new password.
                </p>
              </div>

              {message && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mb-5 flex items-start gap-2.5 p-3.5 rounded-xl border text-xs leading-relaxed ${isDarkMode
                    ? 'border-signal-green/40 bg-signal-green/10 text-signal-green'
                    : 'border-emerald-300 bg-emerald-50 text-emerald-800'
                    }`}
                >
                  <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
                  <span>{message}</span>
                </motion.div>
              )}

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mb-5 flex items-start gap-2.5 p-3.5 rounded-xl border text-xs leading-relaxed ${isDarkMode
                    ? 'border-signal-red/40 bg-signal-red/10 text-signal-red'
                    : 'border-rose-300 bg-rose-50 text-rose-800'
                    }`}
                >
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </motion.div>
              )}

              {!isResetComplete ? (
                <div className="space-y-6">
                  {/* Step 1: Request Code */}
                  <form onSubmit={requestOtp} className="space-y-3">
                    <div>
                      <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="reset-email">
                        Registered Email Address *
                      </label>
                      <div className="relative">
                        <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                          <Mail size={16} />
                        </div>
                        <input
                          id="reset-email"
                          type="email"
                          required
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="officer@agency.gov.in"
                          className={`w-full pl-10 pr-3.5 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={isSending || !email.trim()}
                      className="w-full py-2.5 px-4 rounded-xl border border-signal-blue text-signal-blue hover:bg-signal-blue/10 disabled:opacity-50 text-xs font-bold transition-colors"
                    >
                      {isSending ? 'Sending reset code…' : 'Send Verification Code'}
                    </button>
                  </form>

                  {/* Step 2: Enter OTP & New Password */}
                  <form onSubmit={handleResetPassword} className={`border-t pt-5 space-y-4 ${theme.border}`}>
                    <div>
                      <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="reset-otp">
                        Verification Code *
                      </label>
                      <div className="relative">
                        <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                          <KeyRound size={16} />
                        </div>
                        <input
                          id="reset-otp"
                          type="text"
                          inputMode="numeric"
                          required
                          value={otp}
                          onChange={(e) => setOtp(e.target.value)}
                          placeholder="Enter 6-digit code"
                          className={`w-full pl-10 pr-3.5 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                        />
                      </div>
                    </div>

                    <div>
                      <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="new-password">
                        New Password *
                      </label>
                      <div className="relative">
                        <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                          <Lock size={15} />
                        </div>
                        <input
                          id="new-password"
                          type={showNewPassword ? 'text' : 'password'}
                          required
                          minLength={6}
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder="Min. 6 characters"
                          className={`w-full pl-10 pr-10 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                        />
                        <button
                          type="button"
                          onClick={() => setShowNewPassword((prev) => !prev)}
                          className={`absolute inset-y-0 right-3.5 flex items-center transition-colors hover:text-signal-blue ${theme.muted}`}
                          aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                        >
                          {showNewPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isResetting || !otp.trim() || newPassword.length < 6}
                      className="w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl bg-gradient-to-r from-signal-blue via-signal-blue to-signal-blue/90 hover:from-signal-blue/90 hover:to-signal-blue disabled:opacity-50 text-white font-bold text-sm shadow-lg shadow-signal-blue/30 transition-all hover:shadow-signal-blue/45"
                    >
                      {isResetting ? (
                        <span>Updating password…</span>
                      ) : (
                        <>
                          <span>Reset Password &amp; Proceed</span>
                          <ArrowRight size={16} />
                        </>
                      )}
                    </button>
                  </form>
                </div>
              ) : (
                <div className="text-center py-4 space-y-4">
                  <p className={`text-sm ${theme.subtext}`}>
                    Your account password has been successfully updated. You may now sign in.
                  </p>
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-signal-blue text-white font-bold text-sm shadow-lg shadow-signal-blue/30"
                  >
                    <span>Go to Sign In</span>
                    <ArrowRight size={15} />
                  </Link>
                </div>
              )}

              <div className={`mt-6 pt-5 border-t text-center text-xs transition-colors ${theme.border}`}>
                <Link to="/login" className={`font-semibold transition-colors ${theme.link}`}>
                  &larr; Return to Sign In
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className={`relative z-10 border-t py-6 text-xs transition-colors duration-300 ${isDarkMode ? 'border-white/[0.08] bg-[#0A0D12] text-asphalt-400' : 'border-slate-200 bg-slate-100 text-slate-600'
        }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <p>© {new Date().getFullYear()} RoadSense AI Systems. Municipal Traffic Operations.</p>
          <div className="flex items-center gap-4 text-[11px]">
            <Link to="/" className="hover:text-signal-blue transition-colors">Overview</Link>
            <Link to="/login" className="hover:text-signal-blue transition-colors">Sign In</Link>
            <Link to="/register" className="hover:text-signal-blue transition-colors">Register Account</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}