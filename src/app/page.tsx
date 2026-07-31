"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { api } from "@/lib/api";

const features = [
  {
    icon: "🛡️",
    title: "Risk Analysis",
    description:
      "AI identifies risky clauses like indemnification, IP assignment, and hidden liabilities.",
    gradient: "from-red-500/20 to-orange-500/20",
  },
  {
    icon: "✍️",
    title: "Smart Redlining",
    description:
      "Get AI-suggested revisions for risky clauses. Accept, reject, or customize edits.",
    gradient: "from-blue-500/20 to-cyan-500/20",
  },
  {
    icon: "📊",
    title: "Executive Summaries",
    description:
      "1-page summaries with key terms, obligations, and deadlines extracted automatically.",
    gradient: "from-green-500/20 to-emerald-500/20",
  },
  {
    icon: "🔄",
    title: "Version Comparison",
    description:
      "Compare contract versions side-by-side. Track every change across negotiations.",
    gradient: "from-purple-500/20 to-pink-500/20",
  },
  {
    icon: "⚡",
    title: "Instant Processing",
    description:
      "Upload PDFs, DOCX, or plain text. Get results in minutes, not days.",
    gradient: "from-yellow-500/20 to-amber-500/20",
  },
  {
    icon: "🏛️",
    title: "Compliance Ready",
    description:
      "Check contracts against GDPR, CCPA, and SOC2 requirements automatically.",
    gradient: "from-indigo-500/20 to-violet-500/20",
  },
];

const stats = [
  { value: "10x", label: "Faster Reviews" },
  { value: "95%", label: "Risk Detection" },
  { value: "$500+", label: "Saved per Contract" },
  { value: "24/7", label: "Always Available" },
];

const pricingPlans = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    description: "Try it out",
    features: [
      "3 contract reviews/month",
      "Basic risk flags",
      "PDF & DOCX support",
      "Email support",
    ],
    cta: "Get Started",
    popular: false,
  },
  {
    name: "Professional",
    price: "$49",
    period: "/mo",
    description: "For growing teams",
    features: [
      "25 contracts/month",
      "Full risk analysis",
      "Smart redlining",
      "Executive summaries",
      "Version comparison",
      "Priority support",
    ],
    cta: "Start Free Trial",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For organizations",
    features: [
      "Unlimited contracts",
      "Custom playbook engine",
      "API access",
      "SSO & team management",
      "Dedicated success manager",
      "SLA guarantee",
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handlePricingClick = async (planName: string) => {
    if (planName === "Free") {
      router.push(user ? "/dashboard" : "/login");
      return;
    }
    if (planName === "Enterprise") {
      window.location.href = "mailto:sales@legallens.ai?subject=LegalLens%20Enterprise%20Plan%20Inquiry";
      return;
    }
    if (!user) {
      router.push("/login");
      return;
    }
    try {
      setCheckoutLoading(planName);
      const res = await api.payments.createCheckoutSession("pro");
      if (res.url) {
        window.location.href = res.url;
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Payment checkout failed");
    } finally {
      setCheckoutLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-dark-950 relative overflow-hidden">
      {/* Ambient background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-primary-600/10 rounded-full blur-[120px] animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-600/8 rounded-full blur-[100px] animate-pulse-slow delay-1000" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary-500/5 rounded-full blur-[150px]" />
      </div>

      {/* Navigation */}
      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? "glass py-3" : "py-5"
          }`}
      >
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-sm">
              LL
            </div>
            <span className="text-xl font-bold text-white tracking-tight">
              Legal<span className="gradient-text">Lens</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a
              href="#features"
              className="text-dark-400 hover:text-white transition-colors text-sm"
            >
              Features
            </a>
            <a
              href="#pricing"
              className="text-dark-400 hover:text-white transition-colors text-sm"
            >
              Pricing
            </a>
            <a
              href="#how-it-works"
              className="text-dark-400 hover:text-white transition-colors text-sm"
            >
              How it Works
            </a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-dark-300 hover:text-white transition-colors px-4 py-2"
            >
              Sign In
            </Link>
            <Link
              href="/login"
              className="text-sm bg-primary-600 hover:bg-primary-500 text-white px-5 py-2.5 rounded-xl transition-all hover:shadow-lg hover:shadow-primary-600/25"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-primary-300 mb-8 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            AI-Powered Legal Intelligence
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 animate-slide-up">
            Review Contracts
            <br />
            <span className="gradient-text">in Minutes, Not Days</span>
          </h1>

          <p className="text-lg md:text-xl text-dark-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up [animation-delay:0.15s]">
            AI agents that read, analyze, and redline legal contracts — giving
            you the power of a $500/hr lawyer at a fraction of the cost.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up [animation-delay:0.3s]">
            <Link
              href="/login"
              className="group relative px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white rounded-2xl font-semibold transition-all hover:shadow-xl hover:shadow-primary-600/25 hover:-translate-y-0.5"
            >
              Start Reviewing Contracts
              <span className="ml-2 inline-block group-hover:translate-x-1 transition-transform">
                →
              </span>
            </Link>
            <a
              href="#how-it-works"
              className="px-8 py-4 glass-card text-dark-200 hover:text-white rounded-2xl font-semibold transition-all hover:-translate-y-0.5"
            >
              See How It Works
            </a>
          </div>

          {/* Stats Bar */}
          <div className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
            {stats.map((stat, i) => (
              <div
                key={i}
                className="text-center animate-slide-up"
                style={{ animationDelay: `${0.4 + i * 0.1}s` }}
              >
                <div className="text-3xl md:text-4xl font-bold gradient-text mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-dark-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Mock UI Preview */}
      <section className="relative px-6 pb-20">
        <div className="max-w-5xl mx-auto">
          <div className="glass-card p-2 glow rounded-3xl">
            <div className="bg-dark-900/80 rounded-2xl p-6 relative overflow-hidden">
              {/* Title bar */}
              <div className="flex items-center gap-2 mb-6">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
                <span className="ml-4 text-xs text-dark-500 font-mono">
                  LegalLens AI — Contract Analysis
                </span>
              </div>

              {/* Mock content */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2 space-y-3">
                  <div className="h-4 bg-dark-700/60 rounded-full w-3/4" />
                  <div className="h-4 bg-dark-700/60 rounded-full w-full" />
                  <div className="h-4 bg-dark-700/60 rounded-full w-5/6" />
                  <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-red-500" />
                      <div className="h-3 bg-red-500/30 rounded-full w-32" />
                    </div>
                    <div className="h-3 bg-dark-700/40 rounded-full w-full" />
                    <div className="h-3 bg-dark-700/40 rounded-full w-4/5 mt-1" />
                  </div>
                  <div className="h-4 bg-dark-700/60 rounded-full w-2/3" />
                  <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-yellow-500" />
                      <div className="h-3 bg-yellow-500/30 rounded-full w-28" />
                    </div>
                    <div className="h-3 bg-dark-700/40 rounded-full w-full" />
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="p-4 glass-card rounded-xl">
                    <div className="h-3 bg-primary-500/30 rounded-full w-20 mb-3" />
                    <div className="text-3xl font-bold text-center gradient-text my-2">
                      72
                    </div>
                    <div className="h-2 bg-dark-700/60 rounded-full w-full mt-2" />
                    <div className="flex gap-1 mt-2">
                      <div className="flex-1 h-2 bg-green-500/40 rounded-full" />
                      <div className="flex-1 h-2 bg-yellow-500/40 rounded-full" />
                      <div className="w-8 h-2 bg-red-500/40 rounded-full" />
                    </div>
                  </div>
                  <div className="p-4 glass-card rounded-xl">
                    <div className="h-3 bg-primary-500/30 rounded-full w-24 mb-3" />
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <div className="h-2 bg-dark-700/60 rounded-full w-16" />
                        <div className="w-2 h-2 rounded-full bg-green-500" />
                      </div>
                      <div className="flex justify-between items-center">
                        <div className="h-2 bg-dark-700/60 rounded-full w-20" />
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                      </div>
                      <div className="flex justify-between items-center">
                        <div className="h-2 bg-dark-700/60 rounded-full w-14" />
                        <div className="w-2 h-2 rounded-full bg-yellow-500" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-primary-400 text-sm font-semibold uppercase tracking-wider">
              Features
            </span>
            <h2 className="text-4xl md:text-5xl font-bold mt-3 mb-4">
              Everything You Need to{" "}
              <span className="gradient-text">Review Contracts</span>
            </h2>
            <p className="text-dark-400 text-lg max-w-2xl mx-auto">
              Our AI agents work together to analyze every clause, flag risks,
              and suggest improvements.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <div
                key={i}
                className="group glass-card p-6 hover:bg-white/[0.06] transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-primary-500/5"
              >
                <div
                  className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform`}
                >
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-dark-400 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="relative py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-primary-400 text-sm font-semibold uppercase tracking-wider">
              How It Works
            </span>
            <h2 className="text-4xl md:text-5xl font-bold mt-3 mb-4">
              Three Steps to{" "}
              <span className="gradient-text">Contract Clarity</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Upload",
                desc: "Drag & drop your contract — PDF, DOCX, or plain text. We handle the parsing.",
                icon: "📤",
              },
              {
                step: "02",
                title: "Analyze",
                desc: "Our AI agents scan every clause for risks, obligations, and key terms.",
                icon: "🤖",
              },
              {
                step: "03",
                title: "Review",
                desc: "Get a risk-scored report with redline suggestions and executive summary.",
                icon: "✅",
              },
            ].map((item, i) => (
              <div key={i} className="relative text-center group">
                <div className="text-6xl font-black text-primary-600/10 absolute -top-4 left-1/2 -translate-x-1/2">
                  {item.step}
                </div>
                <div className="relative pt-8">
                  <div className="text-4xl mb-4">{item.icon}</div>
                  <h3 className="text-xl font-bold text-white mb-2">
                    {item.title}
                  </h3>
                  <p className="text-dark-400 text-sm">{item.desc}</p>
                </div>
                {i < 2 && (
                  <div className="hidden md:block absolute top-1/2 -right-4 text-dark-600 text-2xl">
                    →
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="relative py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-primary-400 text-sm font-semibold uppercase tracking-wider">
              Pricing
            </span>
            <h2 className="text-4xl md:text-5xl font-bold mt-3 mb-4">
              Simple, <span className="gradient-text">Transparent Pricing</span>
            </h2>
            <p className="text-dark-400 text-lg">
              Start free. Scale as you grow.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {pricingPlans.map((plan, i) => (
              <div
                key={i}
                className={`relative glass-card p-8 flex flex-col ${plan.popular ? "border-primary-500/30 glow scale-105" : ""
                  }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-primary-600 text-white text-xs font-semibold rounded-full">
                    Most Popular
                  </div>
                )}
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white mb-1">
                    {plan.name}
                  </h3>
                  <p className="text-dark-500 text-sm">{plan.description}</p>
                </div>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-white">
                    {plan.price}
                  </span>
                  <span className="text-dark-500">{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((feat, j) => (
                    <li
                      key={j}
                      className="flex items-center gap-2 text-sm text-dark-300"
                    >
                      <span className="text-primary-400">✓</span>
                      {feat}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => handlePricingClick(plan.name)}
                  disabled={checkoutLoading === plan.name}
                  className={`w-full py-3 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${plan.popular
                    ? "bg-primary-600 hover:bg-primary-500 text-white hover:shadow-lg hover:shadow-primary-600/25"
                    : "glass text-dark-200 hover:text-white hover:bg-white/10"
                    } ${checkoutLoading === plan.name ? "opacity-75 cursor-not-allowed" : ""}`}
                >
                  {checkoutLoading === plan.name ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Redirecting to Stripe...</span>
                    </>
                  ) : (
                    plan.cta
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="glass-card p-12 glow">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to <span className="gradient-text">Save Hours</span> on
              Every Contract?
            </h2>
            <p className="text-dark-400 mb-8">
              Join thousands of businesses using AI to review contracts faster
              and safer.
            </p>
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white rounded-2xl font-semibold transition-all hover:shadow-xl hover:shadow-primary-600/25 hover:-translate-y-0.5"
            >
              Start Free — No Credit Card Required
              <span>→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-xs">
              LL
            </div>
            <span className="text-sm font-semibold text-dark-400">
              LegalLens AI
            </span>
          </div>
          <p className="text-xs text-dark-600">
            © 2026 LegalLens AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
