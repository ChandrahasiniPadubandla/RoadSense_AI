import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  Mail,
  Moon,
  Navigation,
  Phone,
  RotateCcw,
  Shield,
  ShieldCheck,
  Sun,
  User,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PHONE_REGEX = /^(\+91[\-\s]?|0)?[6-9]\d{9}$|^[0-9]{10}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Register() {
  const {
    register,
    requestVerification,
    verifyEmail,
    verifiedEmail,
    markEmailVerified,
    clearEmailVerification,
  } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState(verifiedEmail || location.state?.email || '');
  const [isEmailVerified, setIsEmailVerified] = useState(!!(verifiedEmail || location.state?.verified));

  // Inline OTP states
  const [otp, setOtp] = useState('');
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [otpMessage, setOtpMessage] = useState('');
  const [otpError, setOtpError] = useState('');
  const [countdown, setCountdown] = useState(0);

  // Form states
  const [form, setForm] = useState({
    name: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  // Countdown timer for OTP resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (error) setError('');
  }

  // Step 1: Send verification code to email
  async function handleSendOtp() {
    setOtpError('');
    setOtpMessage('');
    setError('');

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError('Please enter your email address first.');
      return;
    }

    if (!EMAIL_REGEX.test(cleanEmail)) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsSendingOtp(true);
    try {
      await requestVerification(cleanEmail);
      setIsOtpSent(true);
      setCountdown(60);
      setOtpMessage(`Verification code sent to ${cleanEmail}. Check your inbox.`);
    } catch (err) {
      setError(err.message || 'Unable to send verification code. Please check the email.');
    } finally {
      setIsSendingOtp(false);
    }
  }

  // Step 2: Verify the 6-digit OTP code inline
  async function handleVerifyOtp() {
    setOtpError('');
    setOtpMessage('');
    setError('');

    if (otp.length !== 6) {
      setOtpError('Please enter the full 6-digit code.');
      return;
    }

    setIsVerifyingOtp(true);
    try {
      await verifyEmail(email.trim(), otp);
      setIsEmailVerified(true);
      setIsOtpSent(false);
      setOtp('');
      markEmailVerified(email.trim());
      setOtpMessage('');
    } catch (err) {
      setOtpError(err.message || 'Invalid or expired verification code.');
    } finally {
      setIsVerifyingOtp(false);
    }
  }

  // Option to change email if already verified or wrong
  function handleResetEmail() {
    setIsEmailVerified(false);
    setIsOtpSent(false);
    setOtp('');
    setOtpError('');
    setOtpMessage('');
    clearEmailVerification();
  }

  // Final submit: Create user account
  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!isEmailVerified) {
      setError('Please verify your email address before creating an account.');
      return;
    }

    if (!form.name.trim()) {
      setError('Please enter your full name.');
      return;
    }

    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    let validatedPhone = null;
    const trimmedPhone = form.phone.trim();
    if (trimmedPhone) {
      const cleanedPhone = trimmedPhone.replace(/[\s\-()]/g, '');
      if (!PHONE_REGEX.test(cleanedPhone)) {
        setError('Please enter a valid 10-digit phone number (e.g. 9876543210).');
        return;
      }
      validatedPhone = cleanedPhone;
    }

    setIsSubmitting(true);
    try {
      await register({
        name: form.name.trim(),
        email: email.trim(),
        phone: validatedPhone,
        password: form.password,
      });
      clearEmailVerification();
      navigate('/login', { state: { registered: true, email: email.trim() } });
    } catch (err) {
      setError(err.message || 'Unable to create your account. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  // Theme styling tokens
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
    otpBox: isDarkMode
      ? 'border-signal-blue/40 bg-signal-blue/10 text-asphalt-200'
      : 'border-signal-blue/30 bg-blue-50/60 text-slate-800',
    border: isDarkMode ? 'border-white/[0.08]' : 'border-slate-200',
    link: isDarkMode ? 'text-signal-blue hover:text-sky-300' : 'text-signal-blue hover:text-blue-700',
  };

  return (
    <div
      className={`min-h-screen ${theme.root} selection:bg-signal-blue selection:text-white font-sans overflow-x-hidden antialiased transition-colors duration-300 flex flex-col justify-between`}
    >
      {/* ========================================================================= */}
      {/* 1. ULTRA-MODERN BLUEPRINT & GEOMETRIC GRID BACKGROUND                     */}
      {/* ========================================================================= */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Soft Aurora Spotlights */}
        <div
          className={`absolute -top-40 left-1/2 -translate-x-1/2 w-[1200px] h-[700px] blur-[160px] rounded-full transition-colors duration-500 ${isDarkMode
            ? 'bg-gradient-to-b from-signal-blue/25 via-signal-blue/8 to-transparent'
            : 'bg-gradient-to-b from-sky-200/50 via-blue-100/20 to-transparent'
            }`}
        />
        <div
          className={`absolute top-[25%] -left-80 w-[750px] h-[750px] blur-[180px] rounded-full transition-colors duration-500 ${isDarkMode ? 'bg-cyan-500/10' : 'bg-sky-400/10'
            }`}
        />
        <div
          className={`absolute top-[55%] -right-80 w-[750px] h-[750px] blur-[180px] rounded-full transition-colors duration-500 ${isDarkMode ? 'bg-signal-green/10' : 'bg-emerald-400/10'
            }`}
        />

        {/* High-Precision Engineering Grid Lines (48px) */}
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

        {/* Fine Coordinate Dot Intersections (96px) */}
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

        {/* Horizontal Laser Line Accent */}
        <div
          className={`absolute top-20 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent ${isDarkMode ? 'via-white/[0.08]' : 'via-slate-200'
            } to-transparent`}
        />
      </div>

      {/* ========================================================================= */}
      {/* 2. PERMANENTLY FIXED FOCUSED AUTH HEADER                                  */}
      {/* ========================================================================= */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 w-full backdrop-blur-2xl border-b transition-colors duration-300 ${theme.header}`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Brand Identity */}
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

          {/* Right: Theme Toggle & Sign In Link */}
          <div className="flex items-center gap-3">
            {/* Interactive Theme Toggle */}
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

            {/* Quick Sign In CTA */}
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
      {/* 3. SPLIT GRID CONTENT: FEATURE HIGHLIGHTS + REGISTRATION CARD             */}
      {/* ========================================================================= */}
      <main className="relative z-10 flex-grow flex items-center justify-center pt-28 pb-16 md:pt-36 md:pb-20 px-4 sm:px-6">
        <div className="max-w-6xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left Column: Rich Showcase Grid (Visible on lg, adds depth) */}
          <motion.div
            initial={{ opacity: 0, x: -25 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-5 space-y-6 hidden lg:block"
          >
            {/* Back Navigation Arrow + Title Side-by-Side */}
            <div className="flex items-start gap-3.5 sm:gap-4">
              <Link
                to="/"
                className={`inline-flex items-center justify-center w-11 h-11 rounded-2xl border transition-all duration-200 hover:-translate-x-1 shadow-sm shrink-0 mt-1 group ${isDarkMode
                  ? 'border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08] text-asphalt-200 hover:text-white shadow-black/40'
                  : 'border-slate-200 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 shadow-slate-200/60'
                  }`}
                aria-label="Back to Overview"
                title="Back to Overview"
              >
                <ArrowLeft size={20} className="transition-transform group-hover:-translate-x-0.5" />
              </Link>

              <h1 className={`text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight leading-[1.1] ${theme.heading}`}>
                RoadSense AI{' '}
                <span className="bg-gradient-to-r from-sky-400 via-cyan-400 to-signal-green bg-clip-text text-transparent">
                  for Your Department.
                </span>
              </h1>
            </div>

            <p className={`text-base leading-relaxed ${theme.subtext}`}>
              Join traffic police divisions, emergency medical response squads, and urban planners on a unified proactive safety platform.
            </p>

            {/* 3 Tech Feature Cards */}
            <div className="space-y-3.5 pt-2">
              <div className={`p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${theme.infoCard}`}>
                <div className="w-9 h-9 rounded-xl bg-signal-blue/15 text-signal-blue flex items-center justify-center shrink-0 mt-0.5">
                  <Mail size={18} />
                </div>
                <div>
                  <h4 className={`text-xs font-bold ${theme.heading}`}>Instant Email Verification</h4>
                  <p className={`text-[11px] mt-0.5 leading-relaxed ${theme.muted}`}>
                    Quick 6-digit one-time passcode secures official agency accounts immediately.
                  </p>
                </div>
              </div>

              <div className={`p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${theme.infoCard}`}>
                <div className="w-9 h-9 rounded-xl bg-signal-green/15 text-signal-green flex items-center justify-center shrink-0 mt-0.5">
                  <Shield size={18} />
                </div>
                <div>
                  <h4 className={`text-xs font-bold ${theme.heading}`}>Role-Based Operational Portals</h4>
                  <p className={`text-[11px] mt-0.5 leading-relaxed ${theme.muted}`}>
                    Tailored dashboards for Field Officers, Command Admins, and Municipal Observers.
                  </p>
                </div>
              </div>

              <div className={`p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${theme.infoCard}`}>
                <div className="w-9 h-9 rounded-xl bg-signal-amber/15 text-signal-amber flex items-center justify-center shrink-0 mt-0.5">
                  <Zap size={18} />
                </div>
                <div>
                  <h4 className={`text-xs font-bold ${theme.heading}`}>Accelerated Incident Response</h4>
                  <p className={`text-[11px] mt-0.5 leading-relaxed ${theme.muted}`}>
                    Pre-clear congested arterial routes before approaching ambulances encounter delays.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right Column: Registration Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-7 w-full max-w-xl mx-auto"
          >
            {/* Mobile Header (Shown on smaller screens) */}
            <div className="text-center mb-6 lg:hidden relative">
              <Link
                to="/"
                className={`absolute left-0 top-0 inline-flex items-center justify-center w-9 h-9 rounded-xl border transition-all ${isDarkMode
                  ? 'border-white/[0.12] bg-white/[0.04] text-asphalt-200 hover:text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:text-slate-900 shadow-sm'
                  }`}
                aria-label="Back to Overview"
                title="Back to Overview"
              >
                <ArrowLeft size={16} />
              </Link>
              <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-mono mb-3 backdrop-blur-xl ${theme.badge}`}>
                <ShieldCheck size={14} className="text-signal-green" />
                <span>Onboarding</span>
              </div>
              <h2 className={`text-2xl font-black tracking-tight ${theme.heading}`}>
                Create Account
              </h2>
            </div>

            {/* Form Card */}
            <div className={`rounded-3xl border p-6 sm:p-8 backdrop-blur-xl transition-colors duration-300 ${theme.card}`}>
              <div className="hidden lg:block mb-5 pb-3 border-b border-white/[0.08]">
                <h2 className={`text-xl font-bold tracking-tight ${theme.heading}`}>
                  Create Account
                </h2>
                <p className={`mt-1 text-xs ${theme.subtext}`}>
                  {isEmailVerified
                    ? 'Email verified! Complete your operational details below to finalize.'
                    : 'Verify your official email with a 6-digit code to begin registration.'}
                </p>
              </div>

              {/* Error Banner */}
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

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email & Inline Verification Section */}
                <div>
                  <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="email">
                    Official Email Address *
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-grow">
                      <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                        <Mail size={16} />
                      </div>
                      <input
                        id="email"
                        type="email"
                        required
                        disabled={isEmailVerified}
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (error) setError('');
                        }}
                        placeholder="officer@agency.gov.in"
                        className={`w-full pl-10 pr-3.5 py-2.5 rounded-xl border text-sm outline-none transition-colors ${isEmailVerified
                          ? 'border-signal-green/60 bg-signal-green/10 text-signal-green cursor-not-allowed font-medium'
                          : theme.input
                          }`}
                      />
                    </div>

                    {!isEmailVerified ? (
                      <button
                        type="button"
                        onClick={handleSendOtp}
                        disabled={!email.trim() || isSendingOtp || countdown > 0}
                        className="shrink-0 px-4 py-2.5 rounded-xl bg-signal-blue hover:bg-signal-blue/90 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-md shadow-signal-blue/20"
                      >
                        {isSendingOtp ? 'Sending…' : isOtpSent ? 'Resend' : 'Verify Email'}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleResetEmail}
                        className={`shrink-0 px-3.5 py-2.5 rounded-xl border text-xs font-medium transition-colors flex items-center gap-1.5 ${isDarkMode
                          ? 'border-white/[0.12] bg-white/[0.04] text-asphalt-200 hover:text-white'
                          : 'border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200'
                          }`}
                        title="Change verified email"
                      >
                        <RotateCcw size={13} />
                        <span>Change</span>
                      </button>
                    )}
                  </div>

                  {/* Verified Pill */}
                  {isEmailVerified && (
                    <div className="mt-2 flex items-center gap-1.5 text-xs text-signal-green font-medium">
                      <CheckCircle2 size={15} className="shrink-0" />
                      <span>Official Email Verified</span>
                    </div>
                  )}

                  {/* Inline OTP Input Box */}
                  {!isEmailVerified && isOtpSent && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className={`mt-3 p-3.5 rounded-2xl border ${theme.otpBox}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold flex items-center gap-1.5">
                          <KeyRound size={14} className="text-signal-blue" />
                          Enter 6-Digit Verification Code
                        </span>
                        {countdown > 0 && (
                          <span className="text-[11px] font-mono text-signal-blue">
                            Resend in {countdown}s
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <input
                          id="reg-otp"
                          type="text"
                          inputMode="numeric"
                          maxLength={6}
                          value={otp}
                          onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                          placeholder="123456"
                          className={`w-36 text-center py-2 px-3 rounded-xl border text-base font-mono tracking-widest outline-none ${theme.input}`}
                        />
                        <button
                          type="button"
                          onClick={handleVerifyOtp}
                          disabled={otp.length !== 6 || isVerifyingOtp}
                          className="flex-grow py-2 px-4 rounded-xl bg-signal-blue hover:bg-signal-blue/90 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-md shadow-signal-blue/20"
                        >
                          {isVerifyingOtp ? 'Verifying…' : 'Submit Code'}
                        </button>
                      </div>
                      {otpMessage && (
                        <p className="mt-2 text-xs text-signal-green font-medium">{otpMessage}</p>
                      )}
                      {otpError && (
                        <p className="mt-2 text-xs text-signal-red font-medium">{otpError}</p>
                      )}
                    </motion.div>
                  )}
                </div>

                {/* Full Name */}
                <div>
                  <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="name">
                    Full Name &amp; Designation *
                  </label>
                  <div className="relative">
                    <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                      <User size={16} />
                    </div>
                    <input
                      id="name"
                      name="name"
                      type="text"
                      required
                      value={form.name}
                      onChange={handleChange}
                      placeholder="e.g. K. Sharma (Traffic Dept)"
                      className={`w-full pl-10 pr-3.5 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                    />
                  </div>
                </div>

                {/* Phone Number (Optional) */}
                <div>
                  <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="phone">
                    Phone Number
                  </label>
                  <div className="relative">
                    <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                      <Phone size={16} />
                    </div>
                    <input
                      id="phone"
                      name="phone"
                      type="tel"
                      value={form.phone}
                      onChange={handleChange}
                      placeholder="10-digit mobile number (e.g. 9876543210)"
                      className={`w-full pl-10 pr-3.5 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                    />
                  </div>
                </div>

                {/* Passwords Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Password */}
                  <div>
                    <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="password">
                      Password *
                    </label>
                    <div className="relative">
                      <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                        <Lock size={15} />
                      </div>
                      <input
                        id="password"
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        required
                        minLength={6}
                        value={form.password}
                        onChange={handleChange}
                        placeholder="Min. 6 chars"
                        className={`w-full pl-10 pr-10 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        className={`absolute inset-y-0 right-3.5 flex items-center transition-colors hover:text-signal-blue ${theme.muted}`}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label className={`block text-xs font-mono mb-1.5 transition-colors ${theme.label}`} htmlFor="confirmPassword">
                      Confirm Password *
                    </label>
                    <div className="relative">
                      <div className={`absolute inset-y-0 left-3.5 flex items-center pointer-events-none ${theme.muted}`}>
                        <Lock size={15} />
                      </div>
                      <input
                        id="confirmPassword"
                        name="confirmPassword"
                        type={showConfirmPassword ? 'text' : 'password'}
                        required
                        minLength={6}
                        value={form.confirmPassword}
                        onChange={handleChange}
                        placeholder="Repeat password"
                        className={`w-full pl-10 pr-10 py-2.5 rounded-xl border text-sm outline-none transition-colors ${theme.input}`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        className={`absolute inset-y-0 right-3.5 flex items-center transition-colors hover:text-signal-blue ${theme.muted}`}
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                      >
                        {showConfirmPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Submit CTA */}
                <button
                  type="submit"
                  disabled={isSubmitting || !isEmailVerified}
                  className="w-full mt-3 flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl bg-gradient-to-r from-signal-blue via-signal-blue to-signal-blue/90 hover:from-signal-blue/90 hover:to-signal-blue disabled:opacity-50 text-white font-bold text-sm shadow-lg shadow-signal-blue/30 transition-all hover:shadow-signal-blue/45"
                >
                  {isSubmitting ? (
                    <span>Registering account…</span>
                  ) : (
                    <>
                      <span>Complete Registration</span>
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </form>

              {/* Switch to Sign In */}
              <div className={`mt-6 pt-5 border-t text-center text-xs transition-colors ${theme.border}`}>
                <p className={theme.muted}>
                  Already registered with an account?{' '}
                  <Link to="/login" className={`font-semibold ml-1 transition-colors ${theme.link}`}>
                    Sign In &rarr;
                  </Link>
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* ========================================================================= */}
      {/* 4. REFINED FOOTER                                                         */}
      {/* ========================================================================= */}
      <footer className={`relative z-10 border-t py-6 text-xs transition-colors duration-300 ${isDarkMode ? 'border-white/[0.08] bg-[#0A0D12] text-asphalt-400' : 'border-slate-200 bg-slate-100 text-slate-600'
        }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <p>© {new Date().getFullYear()} RoadSense AI Systems. Municipal Traffic Operations.</p>
          <div className="flex items-center gap-4 text-[11px]">
            <Link to="/" className="hover:text-signal-blue transition-colors">Overview</Link>
            <Link to="/login" className="hover:text-signal-blue transition-colors">Sign In</Link>
            <Link to="/forgot-password" className="hover:text-signal-blue transition-colors">Reset Password</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}