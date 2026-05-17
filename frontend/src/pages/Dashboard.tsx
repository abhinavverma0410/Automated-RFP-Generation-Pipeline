import { useEffect, useState } from "react"
import apiClient from "../api/client"
import TenderCard from "../components/TenderCard"
import type { Tender } from "../types/index"

export default function Dashboard() {
    const [tenders, setTenders] = useState<Tender[]>([])
    const [loading, setLoading] = useState<boolean>(true)
    const [error, setError] = useState<string | null>(null)
    const [search, setSearch] = useState<string>("")
    const [scraping, setScraping] = useState<boolean>(false)

    useEffect(() => { fetchTenders() }, [])

    const fetchTenders = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await apiClient.get<Tender[]>("/tenders")
            setTenders(response.data)
        } catch (err) {
            setError("Failed to fetch tenders. Is the backend running?")
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    // Dashboard.tsx
const triggerScrape = async () => {
    try {
        setScraping(true)
        
        await apiClient.post("/scrape")
        
        await fetchTenders()
        
    } catch (err) {
        console.error(err)
        alert("Scraping failed or timed out. Check backend logs.")
    } finally {
        // Turn off the loading state regardless of success or failure
        setScraping(false)
    }
}

    const filteredTenders = tenders.filter(tender =>
        tender.title.toLowerCase().includes(search.toLowerCase()) ||
        tender.organization.toLowerCase().includes(search.toLowerCase())
    )

    const amendedCount = tenders.filter(t => t.is_amended).length
    const draftedCount = tenders.filter(t => t.proposal_drafted).length

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">

            <div className="flex items-start justify-between mb-8">
                <div>
                    <h1 className="text-primary text-2xl font-bold tracking-tight">
                        Tender Opportunities
                    </h1>
                    <p className="text-secondary text-sm mt-1">
                        Canadian government procurement — live from CanadaBuys
                    </p>
                </div>
                <button
                    onClick={triggerScrape}
                    disabled={scraping}
                    className="btn-accent px-4 py-2 font-semibold text-sm rounded disabled:opacity-50"
                >
                    {scraping ? "Scraping..." : "Refresh Now"}
                </button>
            </div>

            {/* Stats bar */}
            <div className="grid grid-cols-3 gap-4 mb-8">
                {[
                    { label: "Total Tenders", value: tenders.length, color: "text-primary" },
                    { label: "Amended", value: amendedCount, color: "text-amber-400" },
                    { label: "Drafted", value: draftedCount, color: "text-emerald-400" },
                ].map(stat => (
                    <div key={stat.label} className="card rounded-lg p-4">
                        <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                        <div className="text-muted text-xs mt-1">{stat.label}</div>
                    </div>
                ))}
            </div>

            {/* Search */}
            <div className="mb-6">
                <input
                    type="text"
                    placeholder="Search by title or organization..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="input-theme w-full rounded-lg px-4 py-3 text-sm"
                />
            </div>

            {loading && (
                <div className="flex items-center justify-center py-20">
                    <div className="spinner w-8 h-8 rounded-full animate-spin"/>
                </div>
            )}

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {!loading && !error && filteredTenders.length === 0 && (
                <div className="text-center py-20">
                    <p className="text-primary text-lg">No tenders found</p>
                    <p className="text-muted text-sm mt-1">
                        {search ? "Try a different search term" : "Click Refresh Now to scrape tenders"}
                    </p>
                </div>
            )}

            {!loading && !error && filteredTenders.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredTenders.map(tender => (
                        <TenderCard key={tender.reference_number} tender={tender} />
                    ))}
                </div>
            )}
        </div>
    )
}