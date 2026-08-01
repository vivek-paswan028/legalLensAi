function getApiBase(): string {
    if (process.env.NEXT_PUBLIC_API_URL) {
        return process.env.NEXT_PUBLIC_API_URL;
    }
    if (typeof window !== "undefined") {
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            if (window.location.port === "3000") {
                return "http://localhost:8000";
            }
        }
    }
    return "";
}

async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string>),
    };

    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const baseUrl = getApiBase();
    const res = await fetch(`${baseUrl}${path}`, {
        ...options,
        headers,
        credentials: "include",
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(error.detail || `Request failed: ${res.status}`);
    }

    return res.json();
}

export interface UserResponse {
    id: string;
    email: string;
    name: string;
    created_at?: string;
}

export interface ContractListItem {
    id: string;
    filename: string;
    status: string;
    contract_type: string;
    uploaded_at: string;
    has_analysis: boolean;
    risk_level: string | null;
    risk_score: number | null;
}

export interface ClauseData {
    id?: string;
    clause_title: string;
    clause_text: string;
    risk_level: "low" | "medium" | "high";
    risk_score: number;
    explanation: string;
    suggested_revision: string | null;
}

export interface AnalysisData {
    overall_risk_score: number;
    overall_risk_level: "low" | "medium" | "high";
    summary: string;
    executive_summary: string;
    key_terms: Record<string, string>;
    parties: string[];
    effective_date: string | null;
    expiration_date: string | null;
    governing_law: string | null;
    analyzed_at: string | null;
    clauses: ClauseData[];
}

export interface ContractDetail {
    id: string;
    filename: string;
    status: string;
    contract_type: string;
    uploaded_at: string;
    analysis: AnalysisData | null;
}

export interface TaskStatus {
    id: string;
    contract_id: string;
    status: "pending" | "running" | "completed" | "failed";
    attempts: number;
    error: string | null;
    created_at: string;
    updated_at: string;
}

export const api = {
    auth: {
        register: (email: string, password: string, name: string) =>
            request<UserResponse>("/api/auth/register", {
                method: "POST",
                body: JSON.stringify({ email, password, name }),
            }),

        login: (email: string, password: string) =>
            request<UserResponse>("/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            }),

        logout: () =>
            request<{ message: string }>("/api/auth/logout", {
                method: "POST",
            }),

        me: () =>
            request<UserResponse>("/api/auth/me"),
    },

    contracts: {
        list: () => request<ContractListItem[]>("/api/contracts"),

        get: (id: string) => request<ContractDetail>(`/api/contracts/${id}`),

        upload: (file: File) => {
            const formData = new FormData();
            formData.append("file", file);
            return request<{ id: string; filename: string; status: string; uploaded_at: string }>(
                "/api/contracts/upload",
                { method: "POST", body: formData }
            );
        },

        delete: (id: string) =>
            request<{ message: string }>(`/api/contracts/${id}`, { method: "DELETE" }),
    },

    analysis: {
        analyze: (contractId: string) =>
            request<{ task_id: string; status: string }>(`/api/analysis/${contractId}/analyze`, {
                method: "POST",
            }),

        getSummary: (contractId: string) =>
            request<{ summary: string; executive_summary: string }>(
                `/api/analysis/${contractId}/summary`
            ),

        getClauses: (contractId: string) =>
            request<{ clauses: ClauseData[] }>(
                `/api/analysis/${contractId}/clauses`
            ),

        getTaskStatus: (contractId: string) =>
            request<TaskStatus>(`/api/analysis/${contractId}/task`),

        saveClauseDecision: (contractId: string, clauseId: string, decision: string, modifiedText?: string) =>
            request<{ message: string }>(
                `/api/analysis/${contractId}/clauses/${clauseId}/decision`,
                {
                    method: "PATCH",
                    body: JSON.stringify({ decision, modified_text: modifiedText }),
                }
            ),

        getDecisions: (contractId: string) =>
            request<{ decisions: Array<{ clause_id: string; decision: string; modified_text: string | null }> }>(
                `/api/analysis/${contractId}/decisions`
            ),
    },

    payments: {
        createCheckoutSession: (tier: string = "pro") =>
            request<{ url: string }>("/api/payments/create-checkout-session", {
                method: "POST",
                body: JSON.stringify({ tier }),
            }),
        getPortalUrl: () =>
            request<{ url: string }>("/api/payments/portal"),
    },

    health: () =>
        request<{ status: string; service: string; llm_provider: string; request_id?: string }>(
            "/api/health"
        ),
};
