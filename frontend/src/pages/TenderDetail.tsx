import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import apiClient from "../api/client"
import ProposalModal from "../components/ProposalModal"
import type { TenderDetail as TenderDetailType, GenerateResponse } from "../types/index"

export default function TenderDetail() {
    const { reference_number } = useParams<{ reference_number: string }>()
    const navigate = useNavigate()
    const [tender, setTender] = useState<TenderDetailType | null>(null)
    const [loading, setLoading] = useState<boolean>(true)
    const [error, setError] = useState<string | null>(null)
    const [generating, setGenerating] = useState<boolean>(false)
    const [proposalContent, setProposalContent] = useState<string | null>(null)
    const [isExistingProposal, setIsExistingProposal] = useState<boolean>(false)

    useEffect(() => {
        if (reference_number) fetchTender()
    }, [reference_number])

    const fetchTender = async () => {
        try {
            setLoading(true)
            const response = await apiClient.get<TenderDetailType>(`/tenders/${reference_number}`)
            setTender(response.data)
        } catch (err) {
            setError("Tender not found")
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const generateProposal = async () => {
        try {
            setGenerating(true)
            const response = await apiClient.post<GenerateResponse>(
                `/tenders/${reference_number}/generate`
            )
            setProposalContent(response.data.draft_content)
            setIsExistingProposal(response.data.already_existed)
            if (tender) setTender({ ...tender, proposal_drafted: true })
        } catch (err) {
            console.error(err)
            alert("Failed to generate proposal. Check backend logs.")
        } finally {
            setGenerating(false)
        }
    }

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen">
            <div className="spinner w-8 h-8 rounded-full animate-spin"/>
        </div>
    )

    if (error || !tender) return (
        <div className="max-w-7xl mx-auto px-6 py-8 text-center">
            <p className="text-secondary">{error || "Tender not found"}</p>
            <button onClick={() => navigate("/")}
                    className="mt-4 text-accent hover:opacity-80 text-sm">
                ← Back to Dashboard
            </button>
        </div>
    )

    return (
        <div className="max-w-4xl mx-auto px-6 py-8">

            <button
                onClick={() => navigate("/")}
                className="text-secondary hover:text-primary text-sm mb-6
                           flex items-center gap-2 transition-colors"
            >
                ← Back to Tenders
            </button>

            {/* Header card */}
            <div className="card rounded-xl p-6 mb-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                    <span className="text-accent text-sm font-mono">
                        {tender.reference_number}
                    </span>
                    <div className="flex gap-2">
                        {tender.is_amended && (
                            <span className="px-2 py-1 bg-amber-500/10 text-amber-400
                                             border border-amber-500/30 rounded text-xs">
                                Amended
                            </span>
                        )}
                        {tender.proposal_drafted && (
                            <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400
                                             border border-emerald-500/30 rounded text-xs">
                                Draft Generated
                            </span>
                        )}
                    </div>
                </div>

                <h1 className="text-primary text-xl font-bold leading-snug mb-4">
                    {tender.title}
                </h1>

                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-muted block text-xs mb-1">Organization</span>
                        <span className="text-secondary">{tender.organization || "Not specified"}</span>
                    </div>
                    <div>
                        <span className="text-muted block text-xs mb-1">Closing Date</span>
                        <span className="text-secondary">{tender.closing_date || "Not specified"}</span>
                    </div>
                    <div className="col-span-2">
                        <span className="text-muted block text-xs mb-1">Source</span>
                        <a href={tender.source_link} target="_blank" rel="noopener noreferrer"
                           className="text-accent hover:opacity-80 text-xs truncate block transition-colors">
                            {tender.source_link}
                        </a>
                    </div>
                </div>
            </div>

            {/* Description */}
            {tender.description && (
                <div className="card rounded-xl p-6 mb-6">
                    <h2 className="text-muted font-semibold mb-3 text-xs uppercase tracking-wider">
                        Description
                    </h2>
                    <p className="text-secondary text-sm leading-relaxed">
                        {tender.description}
                    </p>
                </div>
            )}

            {/* Generate button */}
            <div className="card rounded-xl p-6">
                <h2 className="text-primary font-semibold mb-1">AI Proposal Draft</h2>
                <p className="text-secondary text-sm mb-4">
                    Generate a structured proposal response using Gemini AI
                </p>
                <button
                    onClick={generateProposal}
                    disabled={generating}
                    className="btn-accent px-6 py-3 font-semibold text-sm rounded-lg w-full
                               disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {generating
                        ? "Generating with Gemini AI..."
                        : tender.proposal_drafted
                        ? "View Existing Draft"
                        : "Generate Proposal Draft"
                    }
                </button>
            </div>

            {proposalContent && (
                <ProposalModal
                    content={proposalContent}
                    onClose={() => setProposalContent(null)}
                    isExisting={isExistingProposal}
                />
            )}
        </div>
    )
}