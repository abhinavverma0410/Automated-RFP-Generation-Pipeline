import { useNavigate } from "react-router-dom"
import type { Tender } from "../types/index"

interface TenderCardProps {
    tender: Tender
}

export default function TenderCard({ tender }: TenderCardProps) {
    const navigate = useNavigate()

    return (
        <div
            onClick={() => navigate(`/tenders/${tender.reference_number}`)}
            className="card group rounded-lg p-5 cursor-pointer transition-all duration-200
                       hover:shadow-lg"
        >
            <div className="flex items-start justify-between gap-3 mb-3">
                <span className="text-accent text-xs font-mono font-medium">
                    {tender.reference_number}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                    {tender.is_amended && (
                        <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400
                                         border border-amber-500/30 rounded text-xs font-medium">
                            Amended
                        </span>
                    )}
                    {tender.proposal_drafted && (
                        <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400
                                         border border-emerald-500/30 rounded text-xs font-medium">
                            Drafted
                        </span>
                    )}
                </div>
            </div>

            <h3 className="text-primary font-semibold text-sm leading-snug mb-3
                           transition-colors line-clamp-2">
                {tender.title}
            </h3>

            <div className="flex items-center justify-between text-xs">
                <span className="text-muted truncate mr-4">
                    {tender.organization || "Organization not specified"}
                </span>
                <span className="text-secondary shrink-0">
                    Closes: {tender.closing_date || "N/A"}
                </span>
            </div>

            <div className="mt-4 h-px opacity-0 group-hover:opacity-100 transition-opacity"
                 style={{ background: "linear-gradient(to right, transparent, var(--accent), transparent)" }}/>
        </div>
    )
}