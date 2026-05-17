import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import apiClient from "../api/client"
import ProposalModal from "../components/ProposalModal"
import type { Proposal } from "../types/index"

export default function Proposals() {
    const navigate = useNavigate()
    const [proposals, setProposals] = useState<Proposal[]>([])
    const [loading, setLoading] = useState<boolean>(true)
    const [error, setError] = useState<string | null>(null)
    const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null)
    const [deleting, setDeleting] = useState<string | null>(null) // track which ref is being deleted

    useEffect(() => {
        fetchProposals()
    }, [])

    const fetchProposals = async () => {
        try {
            setLoading(true)
            const response = await apiClient.get<Proposal[]>("/proposals")
            setProposals(response.data)
        } catch (err) {
            setError("Failed to fetch proposals")
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const deleteProposal = async (referenceNumber: string) => {
        // Use a custom toast instead of window.confirm (optional)
        // if (!window.confirm("Permanently delete this proposal draft?")) return

        try {
            setDeleting(referenceNumber)
            await apiClient.delete(`/proposals/${referenceNumber}`)
            setProposals(prev => prev.filter(p => p.reference_number !== referenceNumber))
        } catch (err: any) {
            console.error("Delete failed:", err)
            alert(err?.response?.data?.detail || "Failed to delete proposal.")
        } finally {
            setDeleting(null)
        }
    }

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="mb-8">
                <h1 className="text-primary text-2xl font-bold tracking-tight">
                    Generated Proposals
                </h1>
                <p className="text-secondary text-sm mt-1">
                    AI-drafted bid responses ready for review
                </p>
            </div>

            {loading && (
                <div className="flex items-center justify-center py-20">
                    <div className="spinner w-8 h-8 rounded-full animate-spin" />
                </div>
            )}

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {!loading && !error && proposals.length === 0 && (
                <div className="text-center py-20">
                    <p className="text-primary text-lg">No proposals generated yet</p>
                    <p className="text-muted text-sm mt-1">
                        Go to a tender and click Generate Proposal Draft
                    </p>
                    <button
                        onClick={() => navigate("/")}
                        className="mt-4 text-accent hover:opacity-80 text-sm"
                    >
                        Browse Tenders →
                    </button>
                </div>
            )}

            {!loading && !error && proposals.length > 0 && (
                <div className="flex flex-col gap-4">
                    {proposals.map((proposal) => (
                        <div key={proposal.reference_number} className="card rounded-lg p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <span className="text-accent text-xs font-mono">
                                        {proposal.reference_number}
                                    </span>
                                    <p className="text-muted text-xs mt-1">
                                        Generated: {new Date(proposal.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() =>
                                            navigate(`/tenders/${proposal.reference_number}`)
                                        }
                                        className="px-3 py-1.5 text-secondary border-theme border
                               hover:text-primary rounded text-xs transition-colors"
                                    >
                                        View Tender
                                    </button>
                                    <button
                                        onClick={() => setSelectedProposal(proposal)}
                                        className="btn-outline-accent px-3 py-1.5 rounded text-xs"
                                    >
                                        View Draft
                                    </button>
                                    <button
                                        onClick={() => navigate(`/proposals/${proposal.reference_number}/edit`, { state: { proposalData: proposal } })}
                                        className="px-3 py-1.5 btn-accent rounded text-xs"
                                    >
                                        Edit & Submit
                                    </button>
                                    {/* ── New Delete button ── */}
                                    <button
                                        onClick={() => deleteProposal(proposal.reference_number)}
                                        disabled={deleting === proposal.reference_number}
                                        className="px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/30
                               hover:bg-red-500/20 rounded text-xs transition-colors
                               disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {deleting === proposal.reference_number
                                            ? "Deleting..."
                                            : "🗑 Delete"}
                                    </button>
                                </div>
                            </div>

                            <p className="text-muted text-xs mt-3 leading-relaxed line-clamp-2">
                                {proposal.draft_content.slice(0, 150)}...
                            </p>
                        </div>
                    ))}
                </div>
            )}

            {selectedProposal && (
                <ProposalModal
                    content={selectedProposal.draft_content}
                    onClose={() => setSelectedProposal(null)}
                    isExisting={true}
                />
            )}
        </div>
    )
}