import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CloudRain,
  Compass,
  Copy,
  HeartPulse,
  HelpCircle,
  Mail,
  MapPin,
  Menu,
  MessageSquare,
  Moon,
  Navigation,
  Send,
  Shield,
  ShieldCheck,
  Sun,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from 'lucide-react';

export default function LandingPage() {
  // Mobile menu toggle
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Theme / Mode Toggle — now backed by the app-wide ThemeContext instead of
  // page-local state, so the choice made here carries into the dashboard,
  // login, and every other page (and vice versa).
  const { isDarkMode, toggleTheme } = useTheme();

  // Copy email state
  const [copiedEmail, setCopiedEmail] = useState(false);

  // Contact form state
  const [contactForm, setContactForm] = useState({
    name: '',
    email: '',
    organization: '',
    message: '',
  });
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // FAQ Accordion State
  const [openFaq, setOpenFaq] = useState(0);

  function handleContactChange(e) {
    const { name, value } = e.target;
    setContactForm((prev) => ({ ...prev, [name]: value }));
  }

  function handleContactSubmit(e) {
    e.preventDefault();
    if (!contactForm.name || !contactForm.email || !contactForm.message) return;
    setIsSending(true);
    setTimeout(() => {
      setIsSending(false);
      setFormSubmitted(true);
      setContactForm({ name: '', email: '', organization: '', message: '' });
    }, 600);
  }

  function handleCopyEmail() {
    navigator.clipboard?.writeText('support@Metrivon.ai');
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  }

  const FAQ_ITEMS = [
    {
      q: 'How does Metrivon AI detect traffic hazards early?',
      a: 'The platform continuously monitors arterial speeds, vehicle congestion density, and live meteorological conditions. By cross-referencing road friction and bottleneck patterns with historical incident points, the application flags high-risk corridors minutes before accidents happen, giving police and dispatchers time to intervene.',
    },
    {
      q: 'Who can access the Metrivon Command Center?',
      a: 'The command center is specifically built for municipal traffic police authorities, emergency medical service dispatchers, and urban transportation engineers. Each user group receives an interface tailored to their exact operational scope with role-based access security.',
    },
    {
      q: 'How are emergency services assisted during critical incidents?',
      a: 'When an alert is triggered or extreme risk is forecasted on an arterial route, Metrivon AI activates emergency corridor guidance. Traffic control teams can pre-clear congestion and sync signal timing to prioritize approaching ambulances and rescue vehicles.',
    },
    {
      q: 'Can city planners use this application for urban road planning?',
      a: 'Yes. Metrivon AI securely stores historical flow data, recurring choke point metrics, and incident hotspots. Urban planners can analyze these patterns over time to plan road widening, redesign hazardous intersections, and optimize traffic signal timings.',
    },
    {
      q: 'What makes this different from regular GPS navigation apps?',
      a: 'Consumer GPS apps guide individual drivers after traffic or crashes occur. Metrivon AI is an enterprise command platform for municipal authorities that actively predicts and prevents incidents, manages entire arterial road networks, and coordinates emergency services in real time.',
    },
  ];

  // Theme styling definitions for seamless Dark / Light mode switching
  const theme = {
    root: isDarkMode
      ? 'bg-[#0A0D12] text-asphalt-100'
      : 'bg-[#F8FAFC] text-slate-800',
    header: isDarkMode
      ? 'bg-[#0A0D12]/90 border-white/[0.08]'
      : 'bg-white/90 border-slate-200/90 shadow-sm',
    brandText: isDarkMode ? 'text-white' : 'text-slate-900',
    brandSub: isDarkMode ? 'text-asphalt-400' : 'text-slate-500',
    navPill: isDarkMode
      ? 'bg-white/[0.03] border-white/[0.08]'
      : 'bg-slate-100/90 border-slate-200',
    navLink: isDarkMode
      ? 'text-asphalt-300 hover:text-white hover:bg-white/[0.06]'
      : 'text-slate-600 hover:text-slate-900 hover:bg-white shadow-xs',
    toggleBtn: isDarkMode
      ? 'border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08] text-asphalt-200'
      : 'border-slate-200 bg-slate-100 hover:bg-slate-200/80 text-slate-700',
    signInBtn: isDarkMode
      ? 'text-asphalt-300 hover:text-white hover:bg-white/[0.06]'
      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
    mobileDrawer: isDarkMode
      ? 'border-white/[0.08] bg-[#0A0D12]/98'
      : 'border-slate-200 bg-white/98 shadow-xl',
    heroPill: isDarkMode
      ? 'bg-asphalt-900/90 border-white/[0.12] text-asphalt-200 shadow-black/60'
      : 'bg-white border-slate-200 text-slate-700 shadow-slate-200/60 shadow-lg',
    heading: isDarkMode ? 'text-white' : 'text-slate-900',
    subtext: isDarkMode ? 'text-asphalt-300' : 'text-slate-600',
    muted: isDarkMode ? 'text-asphalt-400' : 'text-slate-500',
    ctaSecondary: isDarkMode
      ? 'bg-asphalt-900/90 hover:bg-asphalt-800 text-asphalt-100 hover:text-white border-white/[0.12] hover:border-signal-blue/40'
      : 'bg-white hover:bg-slate-50 text-slate-800 hover:text-signal-blue border-slate-200 shadow-sm hover:border-signal-blue/50',
    trustBadge: isDarkMode
      ? 'bg-asphalt-900/80 border-white/[0.08] text-asphalt-300'
      : 'bg-white border-slate-200 text-slate-700 shadow-sm',
    sectionAbout: isDarkMode
      ? 'border-white/[0.08] bg-asphalt-900/25 backdrop-blur-[2px]'
      : 'border-slate-200 bg-slate-50/50 backdrop-blur-[2px]',
    sectionFeatures: isDarkMode
      ? 'border-white/[0.08] bg-white/[0.01] backdrop-blur-[2px]'
      : 'border-slate-200/80 bg-white/40 backdrop-blur-[2px]',
    sectionFaq: isDarkMode
      ? 'border-white/[0.08] bg-asphalt-900/30 backdrop-blur-[2px]'
      : 'border-slate-200 bg-slate-50/60 backdrop-blur-[2px]',
    sectionContact: isDarkMode
      ? 'border-t border-white/[0.08] bg-white/[0.01] backdrop-blur-[2px]'
      : 'border-t border-slate-200/80 bg-white/30 backdrop-blur-[2px]',
    card: isDarkMode
      ? 'bg-asphalt-900/80 border-white/[0.08]'
      : 'bg-white border-slate-200 shadow-md shadow-slate-200/50 hover:shadow-lg',
    cardInner: isDarkMode
      ? 'bg-asphalt-950 border-white/[0.1]'
      : 'bg-slate-50 border-slate-200',
    reactiveCard: isDarkMode
      ? 'bg-asphalt-900/50 border-signal-red/20'
      : 'bg-rose-50/60 border-rose-200/80',
    proactiveCard: isDarkMode
      ? 'bg-gradient-to-br from-asphalt-900 via-asphalt-900/95 to-signal-blue/15 border-signal-blue/40 shadow-2xl'
      : 'bg-gradient-to-br from-blue-50 via-white to-emerald-50/40 border-signal-blue/40 shadow-xl',
    faqItemOpen: isDarkMode
      ? 'border-signal-blue/50 bg-asphalt-900/90 shadow-lg shadow-signal-blue/10'
      : 'border-signal-blue/50 bg-blue-50/30 shadow-md shadow-signal-blue/5',
    faqItemClosed: isDarkMode
      ? 'border-white/[0.08] bg-asphalt-900/60 hover:border-white/[0.15]'
      : 'border-slate-200 bg-white hover:border-slate-300 shadow-xs',
    faqDivider: isDarkMode ? 'border-white/[0.04]' : 'border-slate-100',
    contactBox: isDarkMode
      ? 'bg-asphalt-900/90 border-white/[0.1] shadow-2xl'
      : 'bg-white border-slate-200 shadow-xl shadow-slate-200/60',
    input: isDarkMode
      ? 'bg-asphalt-950 border-white/[0.1] text-white focus:border-signal-blue placeholder:text-asphalt-500'
      : 'bg-slate-50 border-slate-200 text-slate-900 focus:bg-white focus:border-signal-blue placeholder:text-slate-400',
    conversionCard: isDarkMode
      ? 'border-signal-blue/40 bg-gradient-to-r from-signal-blue/25 via-asphalt-900 to-signal-blue/15'
      : 'border-signal-blue/30 bg-gradient-to-r from-blue-50 via-white to-sky-50 shadow-xl shadow-blue-100/50',
    conversionBtnSecondary: isDarkMode
      ? 'bg-asphalt-900/90 hover:bg-asphalt-800 text-asphalt-200 hover:text-white border-white/[0.12]'
      : 'bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border-slate-200 shadow-sm',
    footer: isDarkMode
      ? 'border-white/[0.08] bg-[#0A0D12] text-asphalt-400'
      : 'border-slate-200 bg-slate-100 text-slate-600',
    footerLinks: isDarkMode
      ? 'text-asphalt-300 hover:text-white'
      : 'text-slate-600 hover:text-slate-900',
    footerDivider: isDarkMode ? 'border-white/[0.06]' : 'border-slate-200',
    footerPill: isDarkMode
      ? 'bg-white/[0.03] border-white/[0.06] text-asphalt-400'
      : 'bg-white border-slate-200 text-slate-600 shadow-xs',
    border: isDarkMode ? 'border-white/[0.08]' : 'border-slate-200',
  };

  return (
    <div
      className={`min-h-screen ${theme.root} selection:bg-signal-blue selection:text-white font-sans overflow-x-hidden antialiased transition-colors duration-300`}
    >
      {/* ========================================================================= */}
      {/* 1. ULTRA-MODERN AMBIENT BACKGROUND: AURORA MESH & GEOMETRIC GRID         */}
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
        <div
          className={`absolute top-[80%] -left-60 w-[700px] h-[700px] blur-[180px] rounded-full transition-colors duration-500 ${isDarkMode ? 'bg-signal-blue/10' : 'bg-sky-300/15'
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
            maskImage: 'linear-gradient(to bottom, transparent 0%, black 2%, black 98%, transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 2%, black 98%, transparent 100%)',
          }}
        />

        {/* High-Precision Coordinate Intersection Markers (96px) */}
        <div
          className={`absolute inset-0 transition-opacity duration-500 ${isDarkMode ? 'opacity-[0.08]' : 'opacity-[0.11]'
            }`}
          style={{
            backgroundImage: `radial-gradient(circle, ${isDarkMode ? '#3E7CB1' : '#2563EB'
              } 1.5px, transparent 1.5px)`,
            backgroundSize: '96px 96px',
            maskImage: 'linear-gradient(to bottom, transparent 0%, black 2%, black 98%, transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 2%, black 98%, transparent 100%)',
          }}
        />

        {/* Horizontal Laser Line Accent */}
        <div
          className={`absolute top-20 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent ${isDarkMode ? 'via-white/[0.08]' : 'via-slate-200'
            } to-transparent`}
        />
      </div>

      {/* ========================================================================= */}
      {/* 2. PERMANENTLY FIXED HEADER (NEVER MOVES ON SCROLL)                       */}
      {/* ========================================================================= */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 w-full backdrop-blur-2xl border-b transition-colors duration-300 ${theme.header}`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Left: Brand Identity */}
          <Link to="/" className="">
            <div >
              <Navigation size={22} className="" />

            </div>
            <div>
              <div className="flex items-center gap-2">
                <img
      src="images\Merivon_logo.png"
      alt="Metrivon"
      className="h-20 w-20 0-w-[120px] object-contain"
    />
                <span className={`text-xl font-black tracking-tight transition-colors ${theme.brandText}`}>
                  Metrivon
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

          {/* Center: Desktop Nav Links */}
          <nav
            className={`hidden md:flex items-center gap-1 px-3.5 py-1.5 rounded-full backdrop-blur-xl border transition-colors ${theme.navPill}`}
          >
            <a href="#about" className={`px-4 py-1.5 text-xs font-medium rounded-full transition-all ${theme.navLink}`}>
              About
            </a>
            <a href="#features" className={`px-4 py-1.5 text-xs font-medium rounded-full transition-all ${theme.navLink}`}>
              Capabilities
            </a>
            <a href="#faq" className={`px-4 py-1.5 text-xs font-medium rounded-full transition-all ${theme.navLink}`}>
              FAQ
            </a>
            <a href="#contact" className={`px-4 py-1.5 text-xs font-medium rounded-full transition-all ${theme.navLink}`}>
              Contact
            </a>
          </nav>

          {/* Right: Actions (Toggle Button + Auth CTAs + Mobile Menu Toggle) */}
          <div className="flex items-center gap-2.5 sm:gap-3">
            {/* Interactive Theme / Mode Toggle Button */}
            <button
              type="button"
              onClick={toggleTheme}
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

            {/* Auth Buttons */}
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition-colors ${theme.signInBtn}`}
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="hidden sm:flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-signal-blue via-signal-blue to-signal-blue/80 hover:from-signal-blue/90 hover:to-signal-blue text-white text-xs font-bold tracking-wide shadow-lg shadow-signal-blue/25 border border-white/20 transition-colors"
              >
                <span>Register</span>
                <ChevronRight size={13} />
              </Link>
            </div>

            {/* Mobile / Tablet Menu Toggle Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={`md:hidden flex items-center gap-1.5 px-3 py-2 rounded-xl border transition-all ${theme.toggleBtn}`}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
              <span className="text-[11px] font-mono font-medium">
                {mobileMenuOpen ? 'Close' : 'Menu'}
              </span>
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Drawer */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className={`md:hidden border-b backdrop-blur-2xl px-4 pt-3 pb-6 space-y-3 ${theme.mobileDrawer}`}
            >
              <div className="flex flex-col space-y-1">
                <a
                  href="#about"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3.5 py-2.5 text-sm font-medium rounded-xl transition-colors ${theme.navLink}`}
                >
                  About Metrivon AI
                </a>
                <a
                  href="#features"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3.5 py-2.5 text-sm font-medium rounded-xl transition-colors ${theme.navLink}`}
                >
                  Core Capabilities
                </a>
                <a
                  href="#faq"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3.5 py-2.5 text-sm font-medium rounded-xl transition-colors ${theme.navLink}`}
                >
                  Frequently Asked Questions
                </a>
                <a
                  href="#contact"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3.5 py-2.5 text-sm font-medium rounded-xl transition-colors ${theme.navLink}`}
                >
                  Contact &amp; Inquiries
                </a>
              </div>

              <div className={`pt-3 border-t flex flex-col gap-2 ${theme.border}`}>
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`w-full text-center py-2.5 rounded-xl font-semibold text-sm transition-colors ${theme.signInBtn}`}
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center py-2.5 rounded-xl bg-signal-blue hover:bg-signal-blue/90 text-white font-semibold text-sm transition-colors shadow-md"
                >
                  Register Account
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ========================================================================= */}
      {/* 3. HERO SECTION: CUTTING-EDGE TYPOGRAPHY & VISUAL ANCHOR                  */}
      {/* ========================================================================= */}
      <section className="relative z-10 pt-28 pb-24 md:pt-36 md:pb-36">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-4xl mx-auto">
            {/* Main Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className={`text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[1.06] transition-colors ${theme.heading}`}
            >
              Intelligent Roads.{' '}
              <span className="bg-gradient-to-r from-sky-400 via-cyan-400 to-signal-green bg-clip-text text-transparent">
                Zero Blindspots.
              </span>{' '}
              Predictive Safety.
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className={`mt-6 text-base sm:text-xl leading-relaxed max-w-3xl mx-auto font-normal transition-colors ${theme.subtext}`}
            >
              Metrivon AI equips traffic police, municipal authorities, and emergency teams with
              continuous arterial monitoring, predictive hazard warnings, and coordinated green corridors
              before congestion turns into collisions.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Link
                to="/login"
                className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl bg-gradient-to-r from-signal-blue via-signal-blue to-signal-blue/90 hover:from-signal-blue/90 hover:to-signal-blue text-white font-bold text-base shadow-xl shadow-signal-blue/35 border border-white/20 transition-all hover:shadow-signal-blue/55 hover:-translate-y-0.5 group"
              >
                <span>Get Started</span>
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </Link>
              <a
                href="#features"
                className={`w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-4 rounded-xl font-semibold text-base border transition-all backdrop-blur-xl shadow-lg ${theme.ctaSecondary}`}
              >
                <Compass size={17} className="text-signal-blue" />
                <span>Explore Capabilities</span>
              </a>
            </motion.div>

            {/* Value Trust Indicator Badges */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.45 }}
              className="mt-14 flex flex-wrap items-center justify-center gap-3 sm:gap-6 text-xs font-medium"
            >
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border backdrop-blur-lg transition-colors ${theme.trustBadge}`}>
                <CheckCircle2 size={16} className="text-signal-green flex-shrink-0" />
                <span>Proactive Accident Prevention</span>
              </div>
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border backdrop-blur-lg transition-colors ${theme.trustBadge}`}>
                <CheckCircle2 size={16} className="text-signal-green flex-shrink-0" />
                <span>Real-Time Traffic Monitoring</span>
              </div>
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border backdrop-blur-lg transition-colors ${theme.trustBadge}`}>
                <CheckCircle2 size={16} className="text-signal-green flex-shrink-0" />
                <span>Rapid Emergency Dispatch</span>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 4. ABOUT THE APPLICATION: REACTIVE VS PREDICTIVE COMPARISON               */}
      {/* ========================================================================= */}
      <section
        id="about"
        className={`relative z-10 py-24 border-t scroll-mt-16 transition-colors duration-300 ${theme.sectionAbout}`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Content */}
            <div className="lg:col-span-6 space-y-6">
              <span className="text-xs font-mono text-signal-blue uppercase tracking-widest font-bold">
                Why Metrivon AI
              </span>
              <h2 className={`text-3xl sm:text-4xl font-extrabold leading-tight transition-colors ${theme.heading}`}>
                Transforming City Traffic From Reactive Response to Proactive Safety
              </h2>
              <p className={`text-base leading-relaxed transition-colors ${theme.subtext}`}>
                Conventional traffic operations only react after a collision or severe choke point has already stopped traffic. Metrivon AI changes the paradigm by analyzing arterial speeds, density surges, and meteorological friction to neutralize danger zones before collisions occur.
              </p>
              <p className={`text-sm leading-relaxed transition-colors ${theme.muted}`}>
                Municipal traffic police departments, emergency hospital dispatchers, and urban planning engineers gain a single synchronized platform to monitor road health, anticipate accidents, and prioritize rescue routes.
              </p>

              {/* Dedicated Stakeholder Roles */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className={`p-5 rounded-2xl border transition-colors ${theme.card}`}>
                  <div className="flex items-center gap-2 text-signal-blue mb-2">
                    <Users size={18} />
                    <p className={`text-sm font-bold transition-colors ${theme.heading}`}>For Traffic Police</p>
                  </div>
                  <p className={`text-xs leading-relaxed transition-colors ${theme.muted}`}>
                    Monitor corridor flow, adjust signal timings ahead of peak hours, and keep commuter traffic moving safely.
                  </p>
                </div>

                <div className={`p-5 rounded-2xl border transition-colors ${theme.card}`}>
                  <div className="flex items-center gap-2 text-signal-red mb-2">
                    <HeartPulse size={18} />
                    <p className={`text-sm font-bold transition-colors ${theme.heading}`}>For Emergency Units</p>
                  </div>
                  <p className={`text-xs leading-relaxed transition-colors ${theme.muted}`}>
                    Receive instant hazard alerts on dangerous corridors to pre-clear ambulance paths and reduce transit delays.
                  </p>
                </div>
              </div>
            </div>

            {/* Right Split Comparison Deck */}
            <div className="lg:col-span-6 space-y-5">
              {/* Traditional Reactive Card */}
              <div className={`p-6 rounded-2xl border space-y-3 relative overflow-hidden transition-colors ${theme.reactiveCard}`}>
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className={`uppercase font-semibold ${theme.muted}`}>Conventional Approach</span>
                  <span className="text-signal-red font-semibold flex items-center gap-1">
                    <TrendingDown size={14} /> Reactive &amp; Delayed
                  </span>
                </div>
                <p className={`text-base font-bold transition-colors ${theme.heading}`}>
                  Incident Occurs &rarr; Gridlock Forms &rarr; Delayed Response
                </p>
                <p className={`text-xs leading-relaxed transition-colors ${theme.muted}`}>
                  Authorities learn about accidents after traffic has already halted. Ambulances struggle through stationary gridlock, causing secondary collisions and extended transit delays.
                </p>
                <div className="pt-1 flex items-center gap-2 text-[11px] text-signal-red/90 font-mono">
                  <AlertTriangle size={13} />
                  <span>High emergency response lag • Cascading delays</span>
                </div>
              </div>

              {/* Metrivon AI Proactive Card */}
              <div className={`p-6 rounded-2xl border space-y-3 relative transition-colors ${theme.proactiveCard}`}>
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-signal-blue uppercase font-bold">Metrivon AI Standard</span>
                  <span className="text-signal-green font-bold flex items-center gap-1">
                    <TrendingUp size={14} /> Proactive Prevention
                  </span>
                </div>
                <p className={`text-lg font-extrabold transition-colors ${theme.heading}`}>
                  Live Monitoring &rarr; Early Hazard Detection &rarr; Pre-Cleared Routes
                </p>
                <p className={`text-xs leading-relaxed transition-colors ${theme.subtext}`}>
                  Road velocity and friction are evaluated in real time. Choke point surges trigger immediate advisories so officers can balance signal timings and clear emergency routes before collisions occur.
                </p>
                <div className={`pt-2 flex items-center justify-between text-xs font-mono text-signal-green border-t ${theme.border}`}>
                  <span>Target: Zero Preventable Gridlock</span>
                  <CheckCircle2 size={16} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 5. CORE CAPABILITIES (BENTO GRID)                                         */}
      {/* ========================================================================= */}
      <section
        id="features"
        className={`relative z-10 py-24 border-t scroll-mt-16 transition-colors duration-300 ${theme.sectionFeatures}`}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-xl mb-14">
            <h2 className={`text-3xl sm:text-4xl font-extrabold transition-colors ${theme.heading}`}>
              Everything your team needs on one board
            </h2>
            <p className={`mt-3 text-sm leading-relaxed transition-colors ${theme.subtext}`}>
              Built for municipal traffic departments — dispatchers, patrol officers, and control-room
              staff all read from the same live view.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">

            {/* A — Real-Time Monitoring: tall hero card w/ live mockup */}
            <div className={`sm:col-span-2 lg:col-span-2 lg:row-span-2 rounded-3xl border p-8 flex flex-col shadow-lg transition-colors ${theme.card}`}>
              <div className="w-12 h-12 rounded-2xl bg-signal-blue flex items-center justify-center text-white mb-6">
                <Activity size={22} />
              </div>
              <h3 className={`text-xl font-bold mb-2 transition-colors ${theme.heading}`}>
                Real-time traffic monitoring
              </h3>
              <p className={`text-sm leading-relaxed transition-colors ${theme.muted}`}>
                See live speeds, volume, and congestion across every arterial sector, and catch a
                bottleneck the moment it starts to form.
              </p>

              <div className="mt-6 rounded-2xl bg-slate-950 overflow-hidden">
                <div className="flex items-center gap-1.5 px-4 pt-3.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-signal-red/70" />
                  <span className="w-2.5 h-2.5 rounded-full bg-signal-amber/70" />
                  <span className="w-2.5 h-2.5 rounded-full bg-signal-green/70" />
                </div>
                <div className="px-4 py-4 space-y-2 font-mono text-xs text-slate-300">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-signal-green" />
                    SECTOR-14 · 62 km/h · clear
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-signal-amber" />
                    SECTOR-09 · 18 km/h · congested
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-signal-green" />
                    SECTOR-22 · 41 km/h · clear
                  </div>
                </div>
              </div>
            </div>

            {/* B — Accident Risk Forecasting: dark flagship card */}
            <div className="sm:col-span-2 lg:col-span-2 rounded-3xl p-8 bg-slate-950 text-white relative overflow-hidden shadow-lg">
              <AlertTriangle size={180} strokeWidth={1} className="absolute -right-8 -bottom-8 text-signal-red/10" />
              <div className="relative">
                <div className="w-12 h-12 rounded-2xl bg-signal-red/15 border border-signal-red/30 flex items-center justify-center text-signal-red mb-6">
                  <AlertTriangle size={22} />
                </div>
                <h3 className="text-xl font-bold mb-2">Accident risk forecasting</h3>
                <p className="text-sm leading-relaxed text-slate-400">
                  Flag high-probability collision corridors before they happen, by cross-referencing
                  road friction, density, and historical crash clusters.
                </p>
              </div>
            </div>

            {/* C — Weather & Hazard Alerts */}
            <div className={`rounded-3xl border p-7 shadow-lg transition-colors ${theme.card}`}>
              <CloudRain size={22} className="text-signal-amber mb-4" />
              <h3 className={`text-base font-bold mb-1.5 transition-colors ${theme.heading}`}>
                Weather &amp; hazard alerts
              </h3>
              <p className={`text-sm leading-relaxed transition-colors ${theme.muted}`}>
                Tracks rain, fog, and slick asphalt, and raises the alert level the moment conditions
                turn.
              </p>
            </div>

            {/* D — Interactive City Map */}
            <div className={`rounded-3xl border p-7 shadow-lg transition-colors ${theme.card}`}>
              <Compass size={22} className="text-signal-blue mb-4" />
              <h3 className={`text-base font-bold mb-1.5 transition-colors ${theme.heading}`}>
                Interactive city map
              </h3>
              <p className={`text-sm leading-relaxed transition-colors ${theme.muted}`}>
                A vector map with corridor layers, incident history, speed limits, and live lane
                status.
              </p>
            </div>

            {/* E — Emergency Dispatch Support: gradient card */}
            <div className="sm:col-span-2 lg:col-span-2 rounded-3xl p-8 bg-gradient-to-br from-signal-red to-orange-600 text-white relative overflow-hidden shadow-lg">
              <ShieldCheck size={170} strokeWidth={1} className="absolute -right-6 -bottom-10 text-white/10" />
              <div className="relative">
                <span className="inline-flex items-center gap-1.5 text-xs font-medium bg-white/15 px-3 py-1 rounded-full mb-4">
                  Priority routing
                </span>
                <h3 className="text-xl font-bold mb-2">Emergency dispatch support</h3>
                <p className="text-sm leading-relaxed text-white/80">
                  Clears the way for responders with real-time routing and green-wave signal
                  coordination during urgent calls.
                </p>
              </div>
            </div>

            {/* F — Secure Role Portals */}
            <div className={`sm:col-span-2 lg:col-span-2 rounded-3xl border p-7 shadow-lg flex items-start gap-4 transition-colors ${theme.card}`}>
              <div className="w-11 h-11 rounded-full bg-signal-green/15 flex items-center justify-center text-signal-green shrink-0">
                <Shield size={20} />
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <h3 className={`text-base font-bold transition-colors ${theme.heading}`}>Secure role portals</h3>
                  <span className="text-[11px] text-signal-green font-medium">encrypted access</span>
                </div>
                <p className={`mt-1 text-sm leading-relaxed transition-colors ${theme.muted}`}>
                  Separate interfaces for Super Admins, Field Officers, and Municipal Observers, with
                  full audit logging.
                </p>
              </div>
            </div>

          </div>
        </div>
      </section>


      {/* ========================================================================= */}
      {/* 6. INTERACTIVE FAQ ACCORDION                                              */}
      {/* ========================================================================= */}
      <section
        id="faq"
        className={`relative z-10 py-24 border-y scroll-mt-16 transition-colors duration-300 ${theme.sectionFaq}`}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <span className="text-xs font-mono text-signal-blue uppercase tracking-widest font-bold">
              Frequently Asked Questions
            </span>
            <h2 className={`text-3xl sm:text-4xl font-extrabold mt-2 transition-colors ${theme.heading}`}>
              Common Questions About Metrivon AI
            </h2>
            <p className={`mt-3 text-sm transition-colors ${theme.subtext}`}>
              Clear answers regarding platform deployment, roles, and emergency coordination.
            </p>
          </div>

          <div className="space-y-4">
            {FAQ_ITEMS.map((item, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div
                  key={item.q}
                  className={`rounded-2xl border transition-all duration-200 overflow-hidden ${isOpen ? theme.faqItemOpen : theme.faqItemClosed
                    }`}
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaq(isOpen ? -1 : idx)}
                    className={`w-full p-5 text-left flex items-center justify-between text-sm sm:text-base font-bold transition-colors gap-4 ${theme.heading} hover:text-signal-blue`}
                  >
                    <span className="flex items-center gap-3">
                      <HelpCircle size={17} className={isOpen ? 'text-signal-blue' : theme.muted} />
                      <span>{item.q}</span>
                    </span>
                    <ChevronDown
                      size={18}
                      className={`transition-transform duration-200 flex-shrink-0 ${isOpen ? 'rotate-180 text-signal-blue' : theme.muted
                        }`}
                    />
                  </button>
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <div className={`px-5 pb-5 text-xs sm:text-sm leading-relaxed border-t pt-3 ${theme.faqDivider} ${theme.subtext}`}>
                          {item.a}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 7. CONTACT & INQUIRIES SECTION                                            */}
      {/* ========================================================================= */}
      <section id="contact" className={`relative z-10 py-24 scroll-mt-16 transition-colors duration-300 ${theme.sectionContact}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="text-xs font-mono text-signal-blue uppercase tracking-widest font-bold">
              Get In Touch
            </span>
            <h2 className={`text-3xl sm:text-4xl font-extrabold mt-2 transition-colors ${theme.heading}`}>
              Contact &amp; Operational Inquiries
            </h2>
            <p className={`mt-3 text-sm transition-colors ${theme.subtext}`}>
              Have questions regarding system deployment, municipal partnerships, or agency access? Send our operational team a message.
            </p>
          </div>

          <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
            {/* Contact Details Cards */}
            <div className="md:col-span-5 space-y-4">
              <div className={`p-5 rounded-2xl border space-y-3 transition-colors ${theme.card}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-signal-blue/15 text-signal-blue flex items-center justify-center border border-signal-blue/30">
                      <Mail size={18} />
                    </div>
                    <div>
                      <p className={`text-[10px] font-mono uppercase ${theme.muted}`}>Official Email</p>
                      <p className={`text-sm font-semibold transition-colors ${theme.heading}`}>support@Metrivon.ai</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyEmail}
                    className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'bg-asphalt-800 text-asphalt-300 hover:text-white' : 'bg-slate-100 text-slate-600 hover:text-slate-900'
                      }`}
                    title="Copy email to clipboard"
                  >
                    {copiedEmail ? <Check size={14} className="text-signal-green" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>

              <div className={`p-5 rounded-2xl border space-y-3 transition-colors ${theme.card}`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-signal-green/15 text-signal-green flex items-center justify-center border border-signal-green/30">
                    <MapPin size={18} />
                  </div>
                  <div>
                    <p className={`text-[10px] font-mono uppercase ${theme.muted}`}>Operational Center</p>
                    <p className={`text-sm font-semibold transition-colors ${theme.heading}`}>Hyderabad Urban Mobility Center</p>
                    <p className={`text-xs ${theme.muted}`}>Telangana, India</p>
                  </div>
                </div>
              </div>

              <div className={`p-5 rounded-2xl border space-y-3 transition-colors ${theme.card}`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-signal-amber/15 text-signal-amber flex items-center justify-center border border-signal-amber/30">
                    <MessageSquare size={18} />
                  </div>
                  <div>
                    <p className={`text-[10px] font-mono uppercase ${theme.muted}`}>Support Availability</p>
                    <p className={`text-sm font-semibold transition-colors ${theme.heading}`}>24/7 Command Assistance</p>
                    <p className={`text-xs ${theme.muted}`}>Dedicated to registered patrol authorities</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Interactive Contact Form */}
            <div className="md:col-span-7">
              <div className={`p-6 sm:p-8 rounded-3xl border backdrop-blur-xl transition-colors ${theme.contactBox}`}>
                {formSubmitted ? (
                  <div className="py-8 text-center space-y-4">
                    <div className="w-12 h-12 rounded-full bg-signal-green/15 border border-signal-green/30 text-signal-green flex items-center justify-center mx-auto">
                      <CheckCircle2 size={24} />
                    </div>
                    <h3 className={`text-lg font-bold transition-colors ${theme.heading}`}>Inquiry Received</h3>
                    <p className={`text-xs max-w-sm mx-auto leading-relaxed transition-colors ${theme.subtext}`}>
                      Thank you for reaching out to Metrivon AI. Our operational support team will review your inquiry and respond shortly.
                    </p>
                    <button
                      type="button"
                      onClick={() => setFormSubmitted(false)}
                      className="text-xs text-signal-blue hover:underline font-medium pt-2"
                    >
                      Send another message
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleContactSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className={`block text-xs font-mono mb-1 transition-colors ${theme.subtext}`}>
                          Your Name *
                        </label>
                        <input
                          type="text"
                          name="name"
                          required
                          value={contactForm.name}
                          onChange={handleContactChange}
                          placeholder="e.g. Officer K. Sharma"
                          className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${theme.input}`}
                        />
                      </div>
                      <div>
                        <label className={`block text-xs font-mono mb-1 transition-colors ${theme.subtext}`}>
                          Email Address *
                        </label>
                        <input
                          type="email"
                          name="email"
                          required
                          value={contactForm.email}
                          onChange={handleContactChange}
                          placeholder="officer@agency.gov.in"
                          className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${theme.input}`}
                        />
                      </div>
                    </div>

                    <div>
                      <label className={`block text-xs font-mono mb-1 transition-colors ${theme.subtext}`}>
                        Department / Agency
                      </label>
                      <input
                        type="text"
                        name="organization"
                        value={contactForm.organization}
                        onChange={handleContactChange}
                        placeholder="e.g. Hyderabad Traffic Police / Municipal Corp"
                        className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors ${theme.input}`}
                      />
                    </div>

                    <div>
                      <label className={`block text-xs font-mono mb-1 transition-colors ${theme.subtext}`}>
                        Message *
                      </label>
                      <textarea
                        name="message"
                        required
                        rows={4}
                        value={contactForm.message}
                        onChange={handleContactChange}
                        placeholder="Describe your inquiry or deployment request..."
                        className={`w-full px-3.5 py-2.5 rounded-xl border text-sm focus:outline-none transition-colors resize-none ${theme.input}`}
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isSending}
                      className="w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl bg-gradient-to-r from-signal-blue to-signal-blue/90 hover:from-signal-blue/90 hover:to-signal-blue disabled:opacity-50 text-white font-bold text-sm transition-all shadow-lg shadow-signal-blue/25"
                    >
                      {isSending ? (
                        <span>Sending message...</span>
                      ) : (
                        <>
                          <span>Submit Inquiry</span>
                          <Send size={15} />
                        </>
                      )}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 8. CONVERSION CARD                                                        */}
      {/* ========================================================================= */}
      <section className="relative z-10 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div
            className={`relative rounded-3xl p-8 sm:p-14 overflow-hidden border shadow-2xl backdrop-blur-2xl text-center max-w-4xl mx-auto transition-colors duration-300 ${theme.conversionCard}`}
          >
            <div className="absolute -top-24 -right-24 w-72 h-72 bg-signal-blue/20 blur-[100px] rounded-full pointer-events-none" />

            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-signal-blue/15 border border-signal-blue/30 text-signal-blue text-xs font-mono font-semibold mb-4">
              <ShieldCheck size={14} />
              <span>Enterprise Ready</span>
            </div>

            <h2 className={`text-3xl sm:text-4xl font-black tracking-tight transition-colors ${theme.heading}`}>
              Ready to Access the Metrivon Command Center?
            </h2>
            <p className={`mt-3 text-sm sm:text-base max-w-xl mx-auto transition-colors ${theme.subtext}`}>
              Certified municipal officers, dispatch personnel, and traffic authorities can sign in now to inspect real-time corridors, predictive alerts, and safety analytics.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/login"
                className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-signal-blue to-signal-blue/90 hover:from-signal-blue/90 hover:to-signal-blue text-white font-bold text-sm shadow-xl shadow-signal-blue/35 transition-all hover:scale-105"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className={`w-full sm:w-auto px-7 py-4 rounded-xl font-medium text-sm border transition-all ${theme.conversionBtnSecondary}`}
              >
                Register Account
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 9. REFINED ENTERPRISE FOOTER                                              */}
      {/* ========================================================================= */}
      <footer className={`relative z-10 border-t py-12 text-xs transition-colors duration-300 ${theme.footer}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-signal-blue/20 border border-signal-blue/40 text-signal-blue">
                <Navigation size={18} className="transform -rotate-45" />
              </div>
              <div>
                <p className={`text-sm font-bold transition-colors ${theme.heading}`}>Metrivon AI</p>
                <p className={`text-[11px] transition-colors ${theme.muted}`}>Smart Traffic &amp; Accident Prediction System</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-6 font-medium text-xs">
              <a href="#about" className={`transition-colors ${theme.footerLinks}`}>About</a>
              <a href="#features" className={`transition-colors ${theme.footerLinks}`}>Capabilities</a>
              <a href="#faq" className={`transition-colors ${theme.footerLinks}`}>FAQ</a>
              <a href="#contact" className={`transition-colors ${theme.footerLinks}`}>Contact</a>
              <Link to="/login" className={`transition-colors ${theme.footerLinks}`}>Sign In</Link>
            </div>
          </div>

          <div className={`mt-8 pt-8 border-t flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] ${theme.footerDivider}`}>
            <p>© {new Date().getFullYear()} Metrivon AI Systems. All rights reserved.</p>
            <p className="font-mono">Built for municipal resilience &amp; proactive road safety.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
