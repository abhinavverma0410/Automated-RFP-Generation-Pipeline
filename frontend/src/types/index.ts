export interface Tender {
    reference_number: string
    title: string
    organization: string
    closing_date: string
    source_link: string
    is_amended: boolean
    proposal_drafted: boolean
    created_at: string
}

export interface TenderDetail extends Tender {
    description: string
}

export interface Proposal {
    reference_number: string
    draft_content: string
    edited_content: string | null
    status: "draft" | "edited" | "submitted" | "approved" | "rejected"
    submitted_by: string | null
    submitted_at: string | null
    created_at: string
}

export interface GenerateResponse {
    reference_number: string
    draft_content: string
    already_existed: boolean
}