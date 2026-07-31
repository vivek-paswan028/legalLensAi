"use client";

import { useState } from "react";
import { useAuth } from "@/context/auth-context";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function LoginPage() {
    const [isRegister, setIsRegister] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [name, setName] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const { login, register } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            if (isRegister) {
                if (!name.trim()) {
                    setError("Name is required");
                    setLoading(false);
                    return;
                }
                await register(email, password, name);
            } else {
                await login(email, password);
            }
            router.push("/dashboard");
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Something went wrong");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-dark-950 flex items-center justify-center relative px-6">
            {/* Background effects */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] bg-primary-600/10 rounded-full blur-[120px] animate-pulse-slow" />
                <div className="absolute bottom-1/4 right-1/3 w-[400px] h-[400px] bg-blue-600/8 rounded-full blur-[100px] animate-pulse-slow" />
            </div>

            <div className="w-full max-w-md relative">
                {/* Logo */}
                <div className="text-center mb-8">
                    <Link href="/" className="inline-flex items-center gap-2 mb-4">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-sm">
                            LL
                        </div>
                        <span className="text-2xl font-bold text-white tracking-tight">
                            Legal<span className="gradient-text">Lens</span>
                        </span>
                    </Link>
                    <p className="text-dark-400 text-sm">
                        {isRegister
                            ? "Create your account to get started"
                            : "Sign in to your account"}
                    </p>
                </div>

                {/* Form Card */}
                <div className="glass-card p-8 glow-sm">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        {isRegister && (
                            <div>
                                <label className="block text-xs text-dark-400 uppercase tracking-wider font-semibold mb-2">
                                    Full Name
                                </label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="John Doe"
                                    className="w-full px-4 py-3 bg-dark-900/50 border border-white/10 rounded-xl text-white placeholder:text-dark-600 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all text-sm"
                                />
                            </div>
                        )}

                        <div>
                            <label className="block text-xs text-dark-400 uppercase tracking-wider font-semibold mb-2">
                                Email
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@company.com"
                                required
                                className="w-full px-4 py-3 bg-dark-900/50 border border-white/10 rounded-xl text-white placeholder:text-dark-600 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all text-sm"
                            />
                        </div>

                        <div>
                            <label className="block text-xs text-dark-400 uppercase tracking-wider font-semibold mb-2">
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={6}
                                className="w-full px-4 py-3 bg-dark-900/50 border border-white/10 rounded-xl text-white placeholder:text-dark-600 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all text-sm"
                            />
                        </div>

                        {error && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-all hover:shadow-lg hover:shadow-primary-600/25 text-sm"
                        >
                            {loading
                                ? "Please wait..."
                                : isRegister
                                    ? "Create Account"
                                    : "Sign In"}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <button
                            onClick={() => {
                                setIsRegister(!isRegister);
                                setError("");
                            }}
                            className="text-sm text-dark-400 hover:text-primary-400 transition-colors"
                        >
                            {isRegister
                                ? "Already have an account? Sign in"
                                : "Don't have an account? Create one"}
                        </button>
                    </div>
                </div>

                <p className="text-center text-xs text-dark-600 mt-6">
                    By continuing, you agree to our Terms of Service
                </p>
            </div>
        </div>
    );
}
