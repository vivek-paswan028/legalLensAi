"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { api, ContractListItem } from "@/lib/api";

const riskColor: Record<string, string> = {
    low: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    medium: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    high: "text-red-400 bg-red-500/10 border-red-500/20",
};

const riskDot: Record<string, string> = {
    low: "bg-emerald-500",
    medium: "bg-amber-500",
    high: "bg-red-500",
};

export default function DashboardPage() {
    const { user, isAuthenticated, loading: authLoading, logout } = useAuth();
    const router = useRouter();
    const [contracts, setContracts] = useState<ContractListItem[]>([]);
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [loadingContracts, setLoadingContracts] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push("/login");
        }
    }, [authLoading, isAuthenticated, router]);

    const fetchContracts = useCallback(async () => {
        try {
            const data = await api.contracts.list();
            setContracts(data);
        } catch {
            setError("Failed to load contracts");
        } finally {
            setLoadingContracts(false);
        }
    }, []);

    useEffect(() => {
        if (isAuthenticated) {
            fetchContracts();
        }
    }, [isAuthenticated, fetchContracts]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setIsDragging(false);
            const files = Array.from(e.dataTransfer.files);
            handleFiles(files);
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        []
    );

    const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            handleFiles(Array.from(e.target.files));
        }
    };

    const handleFiles = async (files: File[]) => {
        setUploading(true);
        setError("");

        for (const file of files) {
            try {
                const uploaded = await api.contracts.upload(file);

                setContracts((prev) => [
                    {
                        id: uploaded.id,
                        filename: uploaded.filename,
                        status: "analyzing",
                        contract_type: "other",
                        uploaded_at: uploaded.uploaded_at,
                        has_analysis: false,
                        risk_level: null,
                        risk_score: null,
                    },
                    ...prev,
                ]);

                api.analysis
                    .analyze(uploaded.id)
                    .then(({ task_id }) => {
                        pollTaskStatus(uploaded.id, task_id);
                    })
                    .catch(() => {
                        setContracts((prev) =>
                            prev.map((c) =>
                                c.id === uploaded.id ? { ...c, status: "error" } : c
                            )
                        );
                    });
            } catch (err: unknown) {
                setError(
                    err instanceof Error ? err.message : "Failed to upload contract"
                );
            }
        }

        setUploading(false);
    };

    const pollTaskStatus = (contractId: string, taskId: string, maxAttempts = 30) => {
        let attempts = 0;
        const interval = setInterval(async () => {
            attempts++;
            try {
                const task = await api.analysis.getTaskStatus(contractId);
                if (task.status === "completed") {
                    clearInterval(interval);
                    // Refresh contract list to get analysis results
                    fetchContracts();
                } else if (task.status === "failed" || attempts >= maxAttempts) {
                    clearInterval(interval);
                    setContracts((prev) =>
                        prev.map((c) =>
                            c.id === contractId ? { ...c, status: "error" } : c
                        )
                    );
                }
            } catch {
                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    setContracts((prev) =>
                        prev.map((c) =>
                            c.id === contractId ? { ...c, status: "error" } : c
                        )
                    );
                }
            }
        }, 2000);
    };

    const getTimeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime();
        const hours = Math.floor(diff / 3600000);
        if (hours < 1) return "Just now";
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    };

    if (authLoading) {
        return (
            <div className="min-h-screen bg-dark-950 flex items-center justify-center">
                <div className="text-primary-400 animate-pulse text-lg">Loading...</div>
            </div>
        );
    }

    if (!isAuthenticated) return null;

    const riskCounts = {
        high: contracts.filter((c) => c.risk_level === "high").length,
        medium: contracts.filter((c) => c.risk_level === "medium").length,
        low: contracts.filter((c) => c.risk_level === "low").length,
    };

    return (
        <div className="min-h-screen bg-dark-950 relative">
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-primary-600/5 rounded-full blur-[120px]" />
                <div className="absolute bottom-0 left-1/4 w-[400px] h-[400px] bg-blue-600/5 rounded-full blur-[100px]" />
            </div>

            <header className="relative border-b border-white/5 bg-dark-950/80 backdrop-blur-xl">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-xs">
                            LL
                        </div>
                        <span className="text-lg font-bold text-white tracking-tight">
                            Legal<span className="gradient-text">Lens</span>
                        </span>
                    </Link>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-dark-400">{user?.email}</span>
                        <button
                            onClick={() => {
                                logout();
                                router.push("/login");
                            }}
                            className="text-sm text-dark-500 hover:text-red-400 transition-colors"
                        >
                            Sign Out
                        </button>
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-xs font-bold">
                            {user?.name?.charAt(0).toUpperCase() || "U"}
                        </div>
                    </div>
                </div>
            </header>

            <div className="relative max-w-7xl mx-auto px-6 py-10">
                <div className="mb-10">
                    <h1 className="text-3xl font-bold text-white mb-2">
                        Welcome back, {user?.name?.split(" ")[0] || "User"}
                    </h1>
                    <p className="text-dark-400">
                        Upload contracts and let AI do the heavy lifting.
                    </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
                    {[
                        { label: "Total Contracts", value: contracts.length, icon: "📄" },
                        { label: "High Risk", value: riskCounts.high, icon: "🔴" },
                        { label: "Medium Risk", value: riskCounts.medium, icon: "🟡" },
                        { label: "Low Risk", value: riskCounts.low, icon: "🟢" },
                    ].map((stat, i) => (
                        <div key={i} className="glass-card p-5">
                            <div className="flex items-center gap-3">
                                <span className="text-2xl">{stat.icon}</span>
                                <div>
                                    <div className="text-2xl font-bold text-white">
                                        {stat.value}
                                    </div>
                                    <div className="text-xs text-dark-500">{stat.label}</div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {error && (
                    <div className="p-4 mb-6 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                        {error}
                        <button
                            onClick={() => setError("")}
                            className="ml-3 text-red-300 hover:text-white"
                        >
                            ✕
                        </button>
                    </div>
                )}

                <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`glass-card p-10 mb-10 text-center transition-all duration-300 cursor-pointer group ${isDragging
                            ? "border-primary-500/50 bg-primary-500/5 scale-[1.01]"
                            : "hover:border-primary-500/20 hover:bg-white/[0.04]"
                        }`}
                    onClick={() => document.getElementById("file-input")?.click()}
                >
                    <input
                        id="file-input"
                        type="file"
                        className="hidden"
                        accept=".pdf,.docx,.txt"
                        multiple
                        onChange={handleFileInput}
                    />
                    <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">
                        {uploading ? "⏳" : isDragging ? "📥" : "📤"}
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">
                        {isDragging ? "Drop your contract here" : "Upload a Contract"}
                    </h3>
                    <p className="text-dark-500 text-sm mb-4">
                        Drag & drop or click to browse — PDF, DOCX, or TXT
                    </p>
                    <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-sm rounded-xl transition-all">
                        Choose File
                    </div>
                </div>

                <div>
                    <h2 className="text-xl font-semibold text-white mb-4">
                        Your Contracts
                    </h2>

                    {loadingContracts ? (
                        <div className="glass-card p-16 text-center">
                            <div className="text-primary-400 animate-pulse text-lg">
                                Loading contracts...
                            </div>
                        </div>
                    ) : contracts.length === 0 ? (
                        <div className="glass-card p-16 text-center">
                            <div className="text-5xl mb-4">📋</div>
                            <p className="text-dark-400">
                                No contracts yet. Upload your first one above.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {contracts.map((contract) => (
                                <Link
                                    key={contract.id}
                                    href={`/review/${contract.id}`}
                                    className="glass-card p-5 flex items-center justify-between group hover:bg-white/[0.06] transition-all hover:-translate-y-0.5 block"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center text-primary-400 font-mono text-xs">
                                            {contract.filename.split(".").pop()?.toUpperCase()}
                                        </div>
                                        <div>
                                            <h3 className="text-white font-medium group-hover:text-primary-300 transition-colors">
                                                {contract.filename}
                                            </h3>
                                            <p className="text-xs text-dark-500 mt-0.5">
                                                {getTimeAgo(contract.uploaded_at)}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-4">
                                        {contract.status === "analyzing" ? (
                                            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                                                Analyzing...
                                            </span>
                                        ) : contract.status === "error" || contract.status === "failed" ? (
                                            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs bg-red-500/10 text-red-400 border border-red-500/20">
                                                Error
                                            </span>
                                        ) : contract.risk_level ? (
                                            <div className="flex items-center gap-3">
                                                <span
                                                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border ${riskColor[contract.risk_level] || ""
                                                        }`}
                                                >
                                                    <span
                                                        className={`w-1.5 h-1.5 rounded-full ${riskDot[contract.risk_level] || ""
                                                            }`}
                                                    />
                                                    {contract.risk_level.charAt(0).toUpperCase() +
                                                        contract.risk_level.slice(1)}{" "}
                                                    Risk
                                                </span>
                                                <span className="text-sm text-dark-400 font-mono">
                                                    {Math.round((contract.risk_score || 0) * 100)}%
                                                </span>
                                            </div>
                                        ) : null}

                                        <span className="text-dark-600 group-hover:text-primary-400 transition-colors">
                                            →
                                        </span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
