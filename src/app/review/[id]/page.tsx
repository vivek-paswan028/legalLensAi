"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { api, ContractDetail, ClauseData } from "@/lib/api";

const riskColors = {
    low: {
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/20",
        text: "text-emerald-400",
        dot: "bg-emerald-500",
        bar: "bg-emerald-500",
    },
    medium: {
        bg: "bg-amber-500/10",
        border: "border-amber-500/20",
        text: "text-amber-400",
        dot: "bg-amber-500",
        bar: "bg-amber-500",
    },
    high: {
        bg: "bg-red-500/10",
        border: "border-red-500/20",
        text: "text-red-400",
        dot: "bg-red-500",
        bar: "bg-red-500",
    },
};

export default function ReviewPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const { isAuthenticated, loading: authLoading } = useAuth();
    const router = useRouter();

    const [contract, setContract] = useState<ContractDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [activeTab, setActiveTab] = useState<
        "clauses" | "summary" | "redline"
    >("clauses");
    const [expandedClause, setExpandedClause] = useState<number | null>(0);
    const [showRedline, setShowRedline] = useState<number | null>(null);
    const [decisions, setDecisions] = useState<Record<string, { decision: string; modified_text?: string }>>({});
    const [savingDecision, setSavingDecision] = useState<string | null>(null);
    const [taskError, setTaskError] = useState("");
    const [retrying, setRetrying] = useState(false);

    const handleDecision = async (clauseId: string, decision: string, modifiedText?: string) => {
        setSavingDecision(clauseId);
        try {
            await api.analysis.saveClauseDecision(id, clauseId, decision, modifiedText);
            setDecisions((prev) => ({
                ...prev,
                [clauseId]: { decision, modified_text: modifiedText },
            }));
        } catch (err) {
            console.error("Failed to save decision:", err);
        } finally {
            setSavingDecision(null);
        }
    };

    const handleRetry = async () => {
        setRetrying(true);
        setTaskError("");
        try {
            await api.analysis.analyze(id);
            setContract((prev) => prev ? { ...prev, status: "analyzing" } : null);
        } catch (err: unknown) {
            setTaskError(err instanceof Error ? err.message : "Failed to restart analysis");
        } finally {
            setRetrying(false);
        }
    };

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push("/login");
        }
    }, [authLoading, isAuthenticated, router]);

    useEffect(() => {
        if (!isAuthenticated) return;

        const fetchContract = async () => {
            try {
                const data = await api.contracts.get(id);
                setContract(data);
                if (data.status === "failed" || data.status === "error") {
                    try {
                        const taskStatus = await api.analysis.getTaskStatus(id);
                        setTaskError(taskStatus.error || "An unexpected error occurred during contract analysis.");
                    } catch {
                        setTaskError("An unexpected error occurred during contract analysis.");
                    }
                }
            } catch (err: unknown) {
                setError(
                    err instanceof Error ? err.message : "Failed to load contract"
                );
            } finally {
                setLoading(false);
            }
        };

        fetchContract();

        // Poll for analysis completion if contract is being analyzed
        let interval: NodeJS.Timeout;
        if (contract?.status === "analyzing" || contract?.status === "uploaded" || (contract && !contract.analysis && contract.status !== "failed" && contract.status !== "error")) {
            interval = setInterval(async () => {
                try {
                    const data = await api.contracts.get(id);
                    if (data.status === "analyzed") {
                        setContract(data);
                    } else if (data.status === "error" || data.status === "failed") {
                        setContract(data);
                        try {
                            const taskStatus = await api.analysis.getTaskStatus(id);
                            setTaskError(taskStatus.error || "An unexpected error occurred during contract analysis.");
                        } catch {
                            setTaskError("An unexpected error occurred during contract analysis.");
                        }
                    }
                } catch {
                    // Ignore polling errors
                }
            }, 3000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [id, isAuthenticated, contract?.status]);

    useEffect(() => {
        if (!contract?.analysis) return;
        api.analysis.getDecisions(id)
            .then(({ decisions }) => {
                const map: Record<string, { decision: string; modified_text?: string }> = {};
                decisions.forEach((d) => {
                    if (d.clause_id) {
                        map[d.clause_id] = { decision: d.decision, modified_text: d.modified_text || undefined };
                    }
                });
                setDecisions(map);
            })
            .catch(() => {});
    }, [contract?.analysis, id]);

    if (authLoading || loading) {
        return (
            <div className="min-h-screen bg-dark-950 flex items-center justify-center">
                <div className="text-center">
                    <div className="text-4xl animate-pulse mb-4">🔍</div>
                    <div className="text-primary-400 animate-pulse text-lg">
                        Loading analysis...
                    </div>
                </div>
            </div>
        );
    }

    if (error || !contract) {
        return (
            <div className="min-h-screen bg-dark-950 flex items-center justify-center">
                <div className="glass-card p-10 text-center max-w-md">
                    <div className="text-4xl mb-4">⚠️</div>
                    <h2 className="text-xl font-bold text-white mb-2">
                        {error || "Contract not found"}
                    </h2>
                    <Link
                        href="/dashboard"
                        className="text-primary-400 hover:text-primary-300 text-sm"
                    >
                        ← Back to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    const analysis = contract.analysis;

    if (!analysis) {
        if (contract.status === "failed" || contract.status === "error") {
            return (
                <div className="min-h-screen bg-dark-950 flex items-center justify-center p-4">
                    <div className="glass-card p-10 text-center max-w-lg border-red-500/20 shadow-lg shadow-red-500/5">
                        <div className="text-5xl mb-4">⚠️</div>
                        <h2 className="text-2xl font-bold text-white mb-2">
                            Contract Analysis Failed
                        </h2>
                        <p className="text-dark-400 text-sm mb-6">
                            The AI agents encountered an error while reviewing the contract.
                        </p>
                        {taskError && (
                            <div className="bg-red-950/30 border border-red-500/10 rounded-xl p-4 text-left mb-6 font-mono text-xs text-red-300 max-h-40 overflow-y-auto break-all">
                                <span className="font-semibold block text-red-400 uppercase tracking-wider text-[10px] mb-1">Error Details:</span>
                                {taskError}
                            </div>
                        )}
                        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
                            <button
                                onClick={handleRetry}
                                disabled={retrying}
                                className="w-full sm:w-auto px-6 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-medium text-sm rounded-xl transition-all shadow-lg shadow-primary-600/20 flex items-center justify-center gap-2"
                            >
                                {retrying ? (
                                    <>
                                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Retrying...
                                    </>
                                ) : (
                                    <>🔄 Retry Analysis</>
                                )}
                            </button>
                            <Link
                                href="/dashboard"
                                className="w-full sm:w-auto px-6 py-2.5 bg-white/5 hover:bg-white/10 text-dark-300 hover:text-white font-medium text-sm rounded-xl transition-all border border-white/5 flex items-center justify-center"
                            >
                                ← Back to Dashboard
                            </Link>
                        </div>
                    </div>
                </div>
            );
        }

        return (
            <div className="min-h-screen bg-dark-950 flex items-center justify-center">
                <div className="glass-card p-10 text-center max-w-md">
                    <div className="text-4xl animate-pulse mb-4">⏳</div>
                    <h2 className="text-xl font-bold text-white mb-2">
                        {contract.status === "analyzing" || contract.status === "uploaded"
                            ? "Analysis in progress..."
                            : "Not analyzed yet"}
                    </h2>
                    <p className="text-dark-400 text-sm mb-4">
                        {contract.status === "analyzing" || contract.status === "uploaded"
                            ? "Our AI agents are reviewing the contract. This usually takes 30-60 seconds."
                            : "This contract hasn't been analyzed yet."}
                    </p>
                    <Link
                        href="/dashboard"
                        className="text-primary-400 hover:text-primary-300 text-sm"
                    >
                        ← Back to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    const overallColor =
        riskColors[analysis.overall_risk_level] || riskColors.low;
    const clauses = analysis.clauses || [];
    const clausesByRisk = {
        high: clauses.filter((c: ClauseData) => c.risk_level === "high").length,
        medium: clauses.filter((c: ClauseData) => c.risk_level === "medium").length,
        low: clauses.filter((c: ClauseData) => c.risk_level === "low").length,
    };

    return (
        <div className="min-h-screen bg-dark-950 relative">
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-0 left-1/3 w-[400px] h-[400px] bg-primary-600/5 rounded-full blur-[120px]" />
            </div>

            <header className="relative border-b border-white/5 bg-dark-950/80 backdrop-blur-xl">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/dashboard"
                            className="text-dark-400 hover:text-white transition-colors text-sm flex items-center gap-1"
                        >
                            ← Dashboard
                        </Link>
                        <span className="text-dark-600">|</span>
                        <h1 className="text-white font-medium text-sm truncate max-w-md">
                            {contract.filename}
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        <span
                            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border ${overallColor.bg} ${overallColor.border} ${overallColor.text}`}
                        >
                            <span
                                className={`w-1.5 h-1.5 rounded-full ${overallColor.dot}`}
                            />
                            {analysis.overall_risk_level.charAt(0).toUpperCase() +
                                analysis.overall_risk_level.slice(1)}{" "}
                            Risk — {Math.round(analysis.overall_risk_score * 100)}%
                        </span>
                    </div>
                </div>
            </header>

            <div className="relative max-w-7xl mx-auto px-6 py-8">
                <div className="grid lg:grid-cols-4 gap-6">
                    {/* Sidebar */}
                    <div className="lg:col-span-1 space-y-4">
                        <div className="glass-card p-6">
                            <h3 className="text-xs text-dark-500 uppercase tracking-wider font-semibold mb-4">
                                Risk Score
                            </h3>
                            <div className="text-center mb-4">
                                <div className={`text-5xl font-bold ${overallColor.text}`}>
                                    {Math.round(analysis.overall_risk_score * 100)}
                                </div>
                                <div className="text-xs text-dark-500 mt-1">out of 100</div>
                            </div>
                            <div className="h-2 bg-dark-800 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-1000 ${overallColor.bar}`}
                                    style={{
                                        width: `${analysis.overall_risk_score * 100}%`,
                                    }}
                                />
                            </div>
                            <div className="flex justify-between mt-2 text-xs text-dark-600">
                                <span>Safe</span>
                                <span>Risky</span>
                            </div>
                        </div>

                        <div className="glass-card p-6">
                            <h3 className="text-xs text-dark-500 uppercase tracking-wider font-semibold mb-4">
                                Clause Breakdown
                            </h3>
                            <div className="space-y-3">
                                {(["high", "medium", "low"] as const).map((level) => (
                                    <div
                                        key={level}
                                        className="flex items-center justify-between"
                                    >
                                        <span className="flex items-center gap-2 text-sm text-dark-300">
                                            <span
                                                className={`w-2 h-2 rounded-full ${riskColors[level].dot}`}
                                            />
                                            {level.charAt(0).toUpperCase() + level.slice(1)} Risk
                                        </span>
                                        <span
                                            className={`text-sm font-mono ${riskColors[level].text}`}
                                        >
                                            {clausesByRisk[level]}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="glass-card p-6">
                            <h3 className="text-xs text-dark-500 uppercase tracking-wider font-semibold mb-4">
                                Key Details
                            </h3>
                            <div className="space-y-3 text-sm">
                                {analysis.parties && analysis.parties.length > 0 && (
                                    <div>
                                        <span className="text-dark-500">Parties</span>
                                        <div className="text-dark-200 mt-0.5">
                                            {analysis.parties.join(" & ")}
                                        </div>
                                    </div>
                                )}
                                {analysis.effective_date && (
                                    <div>
                                        <span className="text-dark-500">Effective</span>
                                        <div className="text-dark-200 mt-0.5">
                                            {analysis.effective_date}
                                        </div>
                                    </div>
                                )}
                                {analysis.expiration_date && (
                                    <div>
                                        <span className="text-dark-500">Expires</span>
                                        <div className="text-dark-200 mt-0.5">
                                            {analysis.expiration_date}
                                        </div>
                                    </div>
                                )}
                                {analysis.governing_law && (
                                    <div>
                                        <span className="text-dark-500">Governing Law</span>
                                        <div className="text-dark-200 mt-0.5">
                                            {analysis.governing_law}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="lg:col-span-3">
                        <div className="flex gap-1 mb-6 bg-dark-900/50 p-1 rounded-xl w-fit">
                            {(["clauses", "summary", "redline"] as const).map((tab) => (
                                <button
                                    key={tab}
                                    onClick={() => setActiveTab(tab)}
                                    className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === tab
                                            ? "bg-primary-600 text-white shadow-lg shadow-primary-600/20"
                                            : "text-dark-400 hover:text-white hover:bg-white/5"
                                        }`}
                                >
                                    {tab === "clauses"
                                        ? "🛡️ Risk Analysis"
                                        : tab === "summary"
                                            ? "📊 Executive Summary"
                                            : "✍️ Redline View"}
                                </button>
                            ))}
                        </div>

                        {activeTab === "clauses" && (
                            <div className="space-y-4 animate-fade-in">
                                <div className="glass-card p-6">
                                    <h3 className="text-sm font-semibold text-white mb-2">
                                        Analysis Summary
                                    </h3>
                                    <p className="text-sm text-dark-400 leading-relaxed">
                                        {analysis.summary}
                                    </p>
                                </div>

                                {[...clauses]
                                    .sort(
                                        (a: ClauseData, b: ClauseData) =>
                                            b.risk_score - a.risk_score
                                    )
                                    .map((clause: ClauseData, i: number) => {
                                        const colors =
                                            riskColors[clause.risk_level] || riskColors.low;
                                        const isExpanded = expandedClause === i;

                                        return (
                                            <div
                                                key={i}
                                                className={`glass-card overflow-hidden transition-all ${isExpanded ? "ring-1 ring-white/10" : ""
                                                    }`}
                                            >
                                                <button
                                                    onClick={() =>
                                                        setExpandedClause(isExpanded ? null : i)
                                                    }
                                                    className="w-full p-5 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <span
                                                            className={`w-2.5 h-2.5 rounded-full ${colors.dot}`}
                                                        />
                                                        <span className="text-white font-medium">
                                                            {clause.clause_title}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-3">
                                                        <span
                                                            className={`text-sm font-mono ${colors.text}`}
                                                        >
                                                            {Math.round(clause.risk_score * 100)}%
                                                        </span>
                                                        <span
                                                            className={`px-2.5 py-0.5 rounded-full text-xs border ${colors.bg} ${colors.border} ${colors.text}`}
                                                        >
                                                            {clause.risk_level.toUpperCase()}
                                                        </span>
                                                        <span
                                                            className={`text-dark-500 transition-transform ${isExpanded ? "rotate-180" : ""
                                                                }`}
                                                        >
                                                            ▼
                                                        </span>
                                                    </div>
                                                </button>

                                                {isExpanded && (
                                                    <div className="px-5 pb-5 space-y-4 animate-fade-in">
                                                        <div className="border-t border-white/5 pt-4">
                                                            <h4 className="text-xs text-dark-500 uppercase tracking-wider mb-2">
                                                                Clause Text
                                                            </h4>
                                                            <p className="text-sm text-dark-300 leading-relaxed bg-dark-900/50 p-4 rounded-xl border border-white/5">
                                                                &ldquo;{clause.clause_text}&rdquo;
                                                            </p>
                                                        </div>

                                                        <div>
                                                            <h4 className="text-xs text-dark-500 uppercase tracking-wider mb-2">
                                                                AI Analysis
                                                            </h4>
                                                            <p className="text-sm text-dark-300 leading-relaxed">
                                                                {clause.explanation}
                                                            </p>
                                                        </div>

                                                        {clause.suggested_revision && (
                                                            <div>
                                                                <div className="flex items-center justify-between mb-2">
                                                                    <h4 className="text-xs text-dark-500 uppercase tracking-wider">
                                                                        Suggested Revision
                                                                    </h4>
                                                                    <button
                                                                        onClick={() =>
                                                                            setShowRedline(
                                                                                showRedline === i ? null : i
                                                                            )
                                                                        }
                                                                        className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                                                                    >
                                                                        {showRedline === i
                                                                            ? "Hide comparison"
                                                                            : "Show comparison"}
                                                                    </button>
                                                                </div>

                                                                {showRedline === i ? (
                                                                    <div className="grid md:grid-cols-2 gap-3">
                                                                        <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/10">
                                                                            <span className="text-[10px] uppercase tracking-wider text-red-400 font-semibold">
                                                                                Original
                                                                            </span>
                                                                            <p className="text-sm text-dark-400 mt-2 leading-relaxed line-through decoration-red-500/30">
                                                                                {clause.clause_text}
                                                                            </p>
                                                                        </div>
                                                                        <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
                                                                            <span className="text-[10px] uppercase tracking-wider text-emerald-400 font-semibold">
                                                                                Suggested
                                                                            </span>
                                                                            <p className="text-sm text-dark-300 mt-2 leading-relaxed">
                                                                                {clause.suggested_revision}
                                                                            </p>
                                                                        </div>
                                                                    </div>
                                                                ) : (
                                                                    <p className="text-sm text-emerald-300/80 leading-relaxed bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10">
                                                                        {clause.suggested_revision}
                                                                    </p>
                                                                )}

                                                                <div className="flex gap-2 mt-3">
                                                                    <button
                                                                        onClick={() => handleDecision(clause.id!, "accepted")}
                                                                        disabled={savingDecision === clause.id}
                                                                        className="px-4 py-2 text-xs bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg transition-all"
                                                                    >
                                                                        ✓ Accept Revision
                                                                    </button>
                                                                    <button
                                                                        onClick={() => handleDecision(clause.id!, "rejected")}
                                                                        disabled={savingDecision === clause.id}
                                                                        className="px-4 py-2 text-xs glass text-dark-300 hover:text-white rounded-lg transition-all disabled:opacity-50"
                                                                    >
                                                                        ✕ Reject
                                                                    </button>
                                                                    <button
                                                                        onClick={() => {
                                                                            const text = prompt("Enter modified text:", clause.suggested_revision || "");
                                                                            if (text) handleDecision(clause.id!, "modified", text);
                                                                        }}
                                                                        disabled={savingDecision === clause.id}
                                                                        className="px-4 py-2 text-xs glass text-dark-300 hover:text-white rounded-lg transition-all disabled:opacity-50"
                                                                    >
                                                                        ✎ Edit
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                            </div>
                        )}

                        {activeTab === "summary" && (
                            <div className="animate-fade-in space-y-6">
                                <div className="glass-card p-8">
                                    <div className="prose prose-invert prose-sm max-w-none">
                                        <div
                                            dangerouslySetInnerHTML={{
                                                __html: (analysis.executive_summary || "")
                                                    .replace(
                                                        /## /g,
                                                        '<h2 class="text-xl font-bold text-white mt-6 mb-3">'
                                                    )
                                                    .replace(
                                                        /### /g,
                                                        '<h3 class="text-lg font-semibold text-white mt-5 mb-2">'
                                                    )
                                                    .replace(
                                                        /\*\*(.*?)\*\*/g,
                                                        '<strong class="text-white">$1</strong>'
                                                    )
                                                    .replace(
                                                        /- (.*)/g,
                                                        '<li class="text-dark-300 text-sm ml-4">$1</li>'
                                                    )
                                                    .replace(/\n/g, "<br />"),
                                            }}
                                        />
                                    </div>
                                </div>

                                {analysis.key_terms &&
                                    Object.keys(analysis.key_terms).length > 0 && (
                                        <div className="glass-card p-6">
                                            <h3 className="text-sm font-semibold text-white mb-4">
                                                Key Terms at a Glance
                                            </h3>
                                            <div className="grid md:grid-cols-2 gap-4">
                                                {Object.entries(analysis.key_terms).map(
                                                    ([key, value]) => (
                                                        <div
                                                            key={key}
                                                            className="p-3 bg-dark-900/50 rounded-xl border border-white/5"
                                                        >
                                                            <span className="text-xs text-dark-500 capitalize">
                                                                {key.replace(/_/g, " ")}
                                                            </span>
                                                            <p className="text-sm text-dark-200 mt-1">
                                                                {value}
                                                            </p>
                                                        </div>
                                                    )
                                                )}
                                            </div>
                                        </div>
                                    )}
                            </div>
                        )}

                        {activeTab === "redline" && (
                            <div className="animate-fade-in space-y-4">
                                <div className="glass-card p-6">
                                    <h3 className="text-sm font-semibold text-white mb-2">
                                        Smart Redlining
                                    </h3>
                                    <p className="text-sm text-dark-400 mb-4">
                                        AI-suggested revisions for risky clauses. Accept, reject, or
                                        customize each suggestion.
                                    </p>
                                </div>

                                {clauses
                                    .filter((c: ClauseData) => c.suggested_revision)
                                    .map((clause: ClauseData, i: number) => {
                                        const colors =
                                            riskColors[clause.risk_level] || riskColors.low;
                                        return (
                                            <div key={i} className="glass-card p-6">
                                                <div className="flex items-center gap-2 mb-4">
                                                    <span
                                                        className={`w-2 h-2 rounded-full ${colors.dot}`}
                                                    />
                                                    <span className="text-white font-medium text-sm">
                                                        {clause.clause_title}
                                                    </span>
                                                    <span
                                                        className={`ml-auto px-2 py-0.5 rounded-full text-xs border ${colors.bg} ${colors.border} ${colors.text}`}
                                                    >
                                                        {clause.risk_level.toUpperCase()}
                                                    </span>
                                                </div>

                                                <div className="grid md:grid-cols-2 gap-4">
                                                    <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/10">
                                                        <div className="text-[10px] uppercase tracking-wider text-red-400 font-semibold mb-2">
                                                            ✕ Original
                                                        </div>
                                                        <p className="text-sm text-dark-400 leading-relaxed">
                                                            {clause.clause_text}
                                                        </p>
                                                    </div>
                                                    <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
                                                        <div className="text-[10px] uppercase tracking-wider text-emerald-400 font-semibold mb-2">
                                                            ✓ Suggested
                                                        </div>
                                                        <p className="text-sm text-dark-300 leading-relaxed">
                                                            {clause.suggested_revision}
                                                        </p>
                                                    </div>
                                                </div>

                                                <div className="flex gap-2 mt-4">
                                                    <button
                                                        onClick={() => handleDecision(clause.id!, "accepted")}
                                                        disabled={savingDecision === clause.id}
                                                        className="px-4 py-2 text-xs bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg transition-all"
                                                    >
                                                        ✓ Accept
                                                    </button>
                                                    <button
                                                        onClick={() => handleDecision(clause.id!, "rejected")}
                                                        disabled={savingDecision === clause.id}
                                                        className="px-4 py-2 text-xs bg-red-600/20 hover:bg-red-600/30 disabled:opacity-50 text-red-300 rounded-lg transition-all"
                                                    >
                                                        ✕ Reject
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            const text = prompt("Enter modified text:", clause.suggested_revision || "");
                                                            if (text) handleDecision(clause.id!, "modified", text);
                                                        }}
                                                        disabled={savingDecision === clause.id}
                                                        className="px-4 py-2 text-xs glass disabled:opacity-50 text-dark-300 hover:text-white rounded-lg transition-all"
                                                    >
                                                        ✎ Edit Revision
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}

                                {clauses.filter((c: ClauseData) => c.suggested_revision)
                                    .length === 0 && (
                                        <div className="glass-card p-10 text-center">
                                            <div className="text-4xl mb-4">✅</div>
                                            <p className="text-dark-400">
                                                No redline suggestions — all clauses look good!
                                            </p>
                                        </div>
                                    )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
