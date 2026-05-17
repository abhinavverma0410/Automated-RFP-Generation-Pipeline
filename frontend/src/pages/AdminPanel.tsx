import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useUser } from "@clerk/clerk-react"
import { marked } from "marked"
import DOMPurify from "dompurify"
import apiClient from "../api/client"

const ADMIN_USER_ID = "user_3DUETmR7WUiWa8jEvf1S5YcgkrF"

interface AdminProposal {
    reference_number: string
    draft_content: string
    edited_content: string | null
    status: string
    submitted_by: string | null
    submitted_at: string | null
    rejected_at: string | null
    created_at: string
}

interface RecycleBinProposal extends AdminProposal {
    days_remaining: number
}

/**
 * Converts a piece of content (Markdown or HTML) to safe HTML.
 */
function toSafeHTML(content: string): string {
    if (!content) return ""
    const trimmed = content.trim()
    // If it already looks like HTML, sanitize directly
    if (trimmed.startsWith("<")) {
        return DOMPurify.sanitize(content)
    }
    // Otherwise treat it as Markdown, convert, then sanitize
    const html = marked(content) as string
    return DOMPurify.sanitize(html)
}

export default function AdminPanel() {
    const { user } = useUser()
    const navigate = useNavigate()

    const [activeTab, setActiveTab] = useState<"submitted" | "recycle">("submitted")
    const [proposals, setProposals] = useState<AdminProposal[]>([])
    const [recycleBin, setRecycleBin] = useState<RecycleBinProposal[]>([])
    const [loading, setLoading] = useState<boolean>(true)
    const [selectedProposal, setSelectedProposal] = useState<
        AdminProposal | RecycleBinProposal | null
    >(null)
    const [updating, setUpdating] = useState<boolean>(false)
    const [toast, setToast] = useState<string | null>(null)

    const showToast = (message: string) => {
        setToast(message)
        setTimeout(() => setToast(null), 2500)
    }

    useEffect(() => {
        if (user && user.id !== ADMIN_USER_ID) {
            navigate("/")
        }
    }, [user])

    useEffect(() => {
        if (user?.id === ADMIN_USER_ID) {
            fetchAll()
        }
    }, [user])

    const fetchAll = async () => {
        try {
            setLoading(true)
            const [submittedRes, recycleRes] = await Promise.all([
                apiClient.get<AdminProposal[]>("/admin/proposals"),
                apiClient.get<RecycleBinProposal[]>("/admin/recycle-bin"),
            ])
            setProposals(submittedRes.data)
            setRecycleBin(recycleRes.data)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const updateStatus = async (
        reference_number: string,
        status: "approved" | "rejected"
    ) => {
        try {
            setUpdating(true)
            await apiClient.put(`/admin/proposals/${reference_number}/status`, { status })

            if (status === "rejected") {
                const rejected = proposals.find(
                    (p) => p.reference_number === reference_number
                )
                if (rejected) {
                    setProposals((prev) =>
                        prev.filter((p) => p.reference_number !== reference_number)
                    )
                    setRecycleBin((prev) => [
                        ...prev,
                        {
                            ...rejected,
                            status: "rejected",
                            days_remaining: 30,
                            rejected_at: new Date().toISOString(),
                        },
                    ])
                }
            } else {
                setProposals((prev) =>
                    prev.map((p) =>
                        p.reference_number === reference_number ? { ...p, status } : p
                    )
                )
            }

            setSelectedProposal(null)
            showToast(`Proposal ${status} successfully`)
        } catch (err) {
            console.error(err)
            showToast("Failed to update status")
        } finally {
            setUpdating(false)
        }
    }

    const restoreProposal = async (reference_number: string) => {
        try {
            setUpdating(true)
            await apiClient.put(`/admin/proposals/${reference_number}/restore`)

            const restored = recycleBin.find(
                (p) => p.reference_number === reference_number
            )
            if (restored) {
                setRecycleBin((prev) =>
                    prev.filter((p) => p.reference_number !== reference_number)
                )
                setProposals((prev) => [
                    ...prev,
                    { ...restored, status: "submitted", rejected_at: null },
                ])
            }

            setSelectedProposal(null)
            showToast("Proposal restored to submitted")
        } catch (err) {
            console.error(err)
            showToast("Failed to restore proposal")
        } finally {
            setUpdating(false)
        }
    }

    const deleteProposal = async (reference_number: string) => {
        try {
            setUpdating(true)
            await apiClient.delete(`/admin/proposals/${reference_number}`)

            setRecycleBin((prev) =>
                prev.filter((p) => p.reference_number !== reference_number)
            )
            setSelectedProposal(null)
            showToast("Proposal permanently deleted")
        } catch (err) {
            console.error(err)
            showToast("Failed to delete proposal")
        } finally {
            setUpdating(false)
        }
    }

    if (user?.id !== ADMIN_USER_ID) return null

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <span className="px-2 py-0.5 bg-red-500/10 text-red-400 border border-red-500/30 rounded text-xs font-medium">
                        Admin Only
                    </span>
                    <h1 className="text-primary text-2xl font-bold">Admin Panel</h1>
                </div>
                <p className="text-secondary text-sm">
                    Review, approve, reject and manage submitted proposals
                </p>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 mb-6">
                <button
                    onClick={() => {
                        setActiveTab("submitted")
                        setSelectedProposal(null)
                    }}
                    className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === "submitted" ? "btn-accent" : "btn-outline-accent"
                        }`}
                >
                    Submitted
                    {proposals.length > 0 && (
                        <span className="ml-2 px-1.5 py-0.5 bg-white/20 rounded-full text-xs">
                            {proposals.length}
                        </span>
                    )}
                </button>
                <button
                    onClick={() => {
                        setActiveTab("recycle")
                        setSelectedProposal(null)
                    }}
                    className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === "recycle" ? "btn-accent" : "btn-outline-accent"
                        }`}
                >
                    🗑 Recycle Bin
                    {recycleBin.length > 0 && (
                        <span className="ml-2 px-1.5 py-0.5 bg-white/20 rounded-full text-xs">
                            {recycleBin.length}
                        </span>
                    )}
                </button>
            </div>

            {loading && (
                <div className="flex items-center justify-center py-20">
                    <div className="spinner w-8 h-8 rounded-full animate-spin" />
                </div>
            )}

            {/* ── SUBMITTED TAB ── */}
            {!loading && activeTab === "submitted" && (
                <>
                    {proposals.length === 0 ? (
                        <div className="text-center py-20">
                            <p className="text-primary text-lg">No submitted proposals yet</p>
                            <p className="text-muted text-sm mt-1">
                                Proposals submitted by users will appear here
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-3 gap-6">
                            {/* Left list */}
                            <div className="col-span-1 flex flex-col gap-3">
                                {proposals.map((proposal) => (
                                    <div
                                        key={proposal.reference_number}
                                        onClick={() => setSelectedProposal(proposal)}
                                        className="card rounded-lg p-4 cursor-pointer transition-all"
                                        style={{
                                            borderColor:
                                                selectedProposal?.reference_number ===
                                                    proposal.reference_number
                                                    ? "var(--accent)"
                                                    : undefined,
                                        }}
                                    >
                                        <span className="text-accent text-xs font-mono block mb-1">
                                            {proposal.reference_number}
                                        </span>
                                        <span
                                            className={`px-2 py-0.5 rounded text-xs font-medium ${proposal.status === "approved"
                                                    ? "bg-emerald-500/10 text-emerald-400"
                                                    : proposal.status === "rejected"
                                                        ? "bg-red-500/10 text-red-400"
                                                        : "bg-amber-500/10 text-amber-400"
                                                }`}
                                        >
                                            {proposal.status}
                                        </span>
                                        <p className="text-muted text-xs mt-2">
                                            {proposal.submitted_at
                                                ? new Date(proposal.submitted_at).toLocaleDateString()
                                                : "—"}
                                        </p>
                                    </div>
                                ))}
                            </div>

                            {/* Right detail */}
                            <div className="col-span-2">
                                {!selectedProposal ? (
                                    <div className="card rounded-xl p-8 text-center h-full flex items-center justify-center">
                                        <p className="text-muted">Select a proposal to review</p>
                                    </div>
                                ) : (
                                    <div className="card rounded-xl p-6">
                                        <div
                                            className="flex items-center justify-between mb-4 pb-4"
                                            style={{ borderBottom: "1px solid var(--border)" }}
                                        >
                                            <div>
                                                <span className="text-accent text-sm font-mono block">
                                                    {selectedProposal.reference_number}
                                                </span>
                                                <span className="text-muted text-xs">
                                                    Submitted by: {selectedProposal.submitted_by || "Unknown"}
                                                </span>
                                            </div>

                                            {selectedProposal.status === "submitted" && (
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() =>
                                                            updateStatus(
                                                                selectedProposal.reference_number,
                                                                "rejected"
                                                            )
                                                        }
                                                        disabled={updating}
                                                        className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 rounded text-sm transition-colors disabled:opacity-50"
                                                    >
                                                        Reject
                                                    </button>
                                                    <button
                                                        onClick={() =>
                                                            updateStatus(
                                                                selectedProposal.reference_number,
                                                                "approved"
                                                            )
                                                        }
                                                        disabled={updating}
                                                        className="px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 rounded text-sm transition-colors disabled:opacity-50"
                                                    >
                                                        Approve
                                                    </button>
                                                </div>
                                            )}

                                            {selectedProposal.status !== "submitted" && (
                                                <span
                                                    className={`px-3 py-1 rounded text-xs font-medium ${selectedProposal.status === "approved"
                                                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                                            : "bg-red-500/10 text-red-400 border border-red-500/30"
                                                        }`}
                                                >
                                                    {selectedProposal.status.charAt(0).toUpperCase() +
                                                        selectedProposal.status.slice(1)}
                                                </span>
                                            )}
                                        </div>

                                        {/* Proposal content – now converted from Markdown */}
                                        <div
                                            className="tiptap overflow-y-auto max-h-96 text-secondary text-sm leading-relaxed"
                                            dangerouslySetInnerHTML={{
                                                __html: toSafeHTML(
                                                    (selectedProposal as AdminProposal).edited_content ||
                                                    selectedProposal.draft_content
                                                ),
                                            }}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* ── RECYCLE BIN TAB ── */}
            {!loading && activeTab === "recycle" && (
                <>
                    {recycleBin.length === 0 ? (
                        <div className="text-center py-20">
                            <p className="text-primary text-lg">Recycle bin is empty</p>
                            <p className="text-muted text-sm mt-1">
                                Rejected proposals appear here and are auto-deleted after 30 days
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-3 gap-6">
                            {/* Left list */}
                            <div className="col-span-1 flex flex-col gap-3">
                                {recycleBin.map((proposal) => (
                                    <div
                                        key={proposal.reference_number}
                                        onClick={() => setSelectedProposal(proposal)}
                                        className="card rounded-lg p-4 cursor-pointer transition-all"
                                        style={{
                                            borderColor:
                                                selectedProposal?.reference_number ===
                                                    proposal.reference_number
                                                    ? "var(--accent)"
                                                    : undefined,
                                        }}
                                    >
                                        <span className="text-accent text-xs font-mono block mb-2">
                                            {proposal.reference_number}
                                        </span>

                                        <div className="flex items-center justify-between">
                                            <span
                                                className={`text-xs font-medium ${proposal.days_remaining <= 5
                                                        ? "text-red-400"
                                                        : proposal.days_remaining <= 10
                                                            ? "text-amber-400"
                                                            : "text-muted"
                                                    }`}
                                            >
                                                {proposal.days_remaining === 0
                                                    ? "Deleting soon..."
                                                    : `${proposal.days_remaining} days left`}
                                            </span>
                                        </div>

                                        <div
                                            className="mt-2 h-1 rounded-full overflow-hidden"
                                            style={{ backgroundColor: "var(--border)" }}
                                        >
                                            <div
                                                className="h-full rounded-full transition-all"
                                                style={{
                                                    width: `${(proposal.days_remaining / 30) * 100}%`,
                                                    backgroundColor:
                                                        proposal.days_remaining <= 5
                                                            ? "#f87171"
                                                            : proposal.days_remaining <= 10
                                                                ? "#fbbf24"
                                                                : "var(--accent)",
                                                }}
                                            />
                                        </div>

                                        <p className="text-muted text-xs mt-2">
                                            Rejected:{" "}
                                            {proposal.rejected_at
                                                ? new Date(proposal.rejected_at).toLocaleDateString()
                                                : "—"}
                                        </p>
                                    </div>
                                ))}
                            </div>

                            {/* Right detail */}
                            <div className="col-span-2">
                                {!selectedProposal ? (
                                    <div className="card rounded-xl p-8 text-center h-full flex items-center justify-center">
                                        <p className="text-muted">Select a proposal to review</p>
                                    </div>
                                ) : (
                                    <div className="card rounded-xl p-6">
                                        <div
                                            className="flex items-center justify-between mb-4 pb-4"
                                            style={{ borderBottom: "1px solid var(--border)" }}
                                        >
                                            <div>
                                                <span className="text-accent text-sm font-mono block">
                                                    {selectedProposal.reference_number}
                                                </span>
                                                <span className="text-muted text-xs">
                                                    {(selectedProposal as RecycleBinProposal).days_remaining}{" "}
                                                    days until auto-deletion
                                                </span>
                                            </div>

                                            <div className="flex gap-3">
                                                <button
                                                    onClick={() =>
                                                        restoreProposal(selectedProposal.reference_number)
                                                    }
                                                    disabled={updating}
                                                    className="px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 rounded text-sm transition-colors disabled:opacity-50"
                                                >
                                                    ↩ Restore
                                                </button>

                                                <button
                                                    onClick={() =>
                                                        deleteProposal(selectedProposal.reference_number)
                                                    }
                                                    disabled={updating}
                                                    className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 rounded text-sm transition-colors disabled:opacity-50"
                                                >
                                                    🗑 Delete Forever
                                                </button>
                                            </div>
                                        </div>

                                        <div
                                            className="tiptap overflow-y-auto max-h-96 text-secondary text-sm leading-relaxed"
                                            dangerouslySetInnerHTML={{
                                                __html: toSafeHTML(
                                                    (selectedProposal as AdminProposal).edited_content ||
                                                    selectedProposal.draft_content
                                                ),
                                            }}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Toast notification */}
            <div
                className="fixed bottom-8 transition-all duration-300"
                style={{
                    left: "50%",
                    zIndex: 100,
                    transform: toast
                        ? "translateX(-50%) translateY(0)"
                        : "translateX(-50%) translateY(80px)",
                    opacity: toast ? 1 : 0,
                    pointerEvents: "none",
                }}
            >
                <div
                    className="flex items-center gap-2 px-5 py-3 rounded-lg shadow-xl"
                    style={{
                        backgroundColor: "var(--bg-card)",
                        border: "1px solid var(--accent-border)",
                    }}
                >
                    <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 text-xs">
                        ✓
                    </div>
                    <span className="text-primary text-sm font-medium whitespace-nowrap">
                        {toast}
                    </span>
                </div>
            </div>
        </div>
    )
}