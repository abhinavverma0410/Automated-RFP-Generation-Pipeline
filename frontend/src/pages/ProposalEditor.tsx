import { useEffect, useState } from "react"
import { useParams, useNavigate, useLocation } from "react-router-dom"
import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import HorizontalRule from "@tiptap/extension-horizontal-rule"
import Typography from "@tiptap/extension-typography"
import Placeholder from "@tiptap/extension-placeholder"
import { InputRule } from "@tiptap/core"
import { marked } from "marked"
import DOMPurify from "dompurify"
import { useUser } from "@clerk/clerk-react"
import apiClient from "../api/client"
import type { Proposal } from "../types/index"

// Custom horizontal rule extension that creates <hr> on typing '--- '
const CustomHorizontalRule = HorizontalRule.extend({
    addInputRules() {
        return [
            new InputRule({
                find: /^---\s$/,
                handler: ({ state, range }) => {
                    state.tr.delete(range.from, range.to)
                    const hrNode = state.schema.nodes.horizontalRule?.create()
                    if (hrNode) {
                        state.tr.insert(range.from, hrNode)
                    }
                },
            }),
        ]
    },
})

export default function ProposalEditor() {
    const { reference_number } = useParams<{ reference_number: string }>()
    const navigate = useNavigate()
    const { user } = useUser()

    const location = useLocation();
    const passedProposal = location.state?.proposalData;

    const [proposal, setProposal] = useState(passedProposal || null);
    const [loading, setLoading] = useState(!passedProposal);
    const [saving, setSaving] = useState<boolean>(false)
    const [submitting, setSubmitting] = useState<boolean>(false)
    const [saved, setSaved] = useState<boolean>(false)
    const [error, setError] = useState<string | null>(null)
    const [toast, setToast] = useState<string | null>(null)

    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                heading: {
                    levels: [1, 2, 3],
                },
                bold: {},
                italic: {},
                bulletList: {},
                orderedList: {},
                blockquote: {},
            }),
            Typography,
            Placeholder.configure({
                placeholder: "Start editing your proposal here...",
            }),
            CustomHorizontalRule,
            // No Markdown extension needed – we handle paste manually
        ],
        content: "",
        editorProps: {
            attributes: {
                class: "focus:outline-none min-h-96 p-6 text-sm leading-relaxed",
            },
        },
    })

    // ── Paste handler: convert Markdown to HTML automatically ──
    useEffect(() => {
        if (!editor) return

        const handlePaste = (event: ClipboardEvent) => {
            const text = event.clipboardData?.getData("text/plain")
            if (!text) return

            // Quick detection: does it look like Markdown?
            // Matches lines starting with #, -, *, >, `, 1., ---
            const looksLikeMarkdown =
                /^(?:\s*(#{1,3}\s|[-*]\s|>\s|```|[0-9]+\.\s|---\s?))/m.test(text)
            if (!looksLikeMarkdown) return

            event.preventDefault()

            // Convert Markdown → sanitized HTML and insert at cursor
            const html = DOMPurify.sanitize(marked(text) as string)
            editor.chain().focus().insertContent(html).run()
        }

        const editorElement = editor.view.dom
        editorElement.addEventListener("paste", handlePaste)
        return () => editorElement.removeEventListener("paste", handlePaste)
    }, [editor])

    if (!editor) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="spinner w-8 h-8 rounded-full animate-spin" />
            </div>
        )
    }

    const showToast = (message: string) => {
        setToast(message)
        setTimeout(() => setToast(null), 2500)
    }

    useEffect(() => {
        if (reference_number) fetchProposal()
    }, [reference_number])

    const fetchProposal = async () => {
        try {
            setLoading(true)
            const response = await apiClient.get<Proposal>(
                `/proposals/${reference_number}`
            )
            setProposal(response.data)

            const rawContent = response.data.edited_content ?? response.data.draft_content

            // Check if existing content is HTML or Markdown
            const isHTML = rawContent.trim().startsWith("<")
            const htmlContent = DOMPurify.sanitize(
                isHTML ? rawContent : await marked(rawContent)
            )

            setTimeout(() => {
                editor?.commands.setContent(htmlContent)
            }, 0)
        } catch (err) {
            setError("Proposal not found")
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const saveProposal = async () => {
        if (!editor) return

        try {
            setSaving(true)
            const edited_content = editor.getHTML()
            await apiClient.put(`/proposals/${reference_number}`, {
                edited_content,
            })
            setSaved(true)
            setTimeout(() => setSaved(false), 3000)
        } catch (err) {
            console.error(err)
            showToast("Failed to save. Please try again.")
        } finally {
            setSaving(false)
        }
    }

    const submitProposal = async () => {
        if (!editor || !user) return

        try {
            setSubmitting(true)
            await saveProposal()

            await apiClient.post(`/proposals/${reference_number}/submit`, {
                user_id: user.id,
            })

            if (proposal) {
                setProposal({ ...proposal, status: "submitted" })
            }

            showToast("Proposal submitted successfully!")
            setTimeout(() => navigate("/proposals"), 1500)
        } catch (err) {
            console.error(err)
            showToast("Failed to submit. Please try again.")
        } finally {
            setSubmitting(false)
        }
    }

    // ── Loading state ──
    if (loading)
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="spinner w-8 h-8 rounded-full animate-spin" />
            </div>
        )

    // ── Error state ──
    if (error || !proposal)
        return (
            <div className="max-w-4xl mx-auto px-6 py-8 text-center">
                <p className="text-secondary">{error || "Proposal not found"}</p>
                <button
                    onClick={() => navigate("/proposals")}
                    className="mt-4 text-accent hover:opacity-80 text-sm"
                >
                    ← Back to Proposals
                </button>
            </div>
        )

    const status = proposal.status ?? "draft"
    const isSubmitted =
        status === "submitted" || status === "approved" || status === "rejected"
    
    if (loading || !proposal) {
        return <div>Loading...</div>;
    }
    return (
        <div className="max-w-5xl mx-auto px-6 py-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <button
                    onClick={() => navigate("/proposals")}
                    className="text-secondary hover:text-primary text-sm flex items-center gap-2 transition-colors"
                >
                    ← Back to Proposals
                </button>

                <span
                    className={`px-3 py-1 rounded-full text-xs font-medium border ${status === "submitted"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                        : status === "approved"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : status === "rejected"
                                ? "bg-red-500/10 text-red-400 border-red-500/30"
                                : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                        }`}
                >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                </span>
            </div>

            {/* Title */}
            <div className="mb-6">
                <h1 className="text-primary text-2xl font-bold">Proposal Editor</h1>
                <p className="text-muted text-sm mt-1 font-mono">{reference_number}</p>
            </div>

            {/* Submitted notice */}
            {isSubmitted && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-amber-400 text-sm mb-6">
                    This proposal has been submitted and can no longer be edited.
                </div>
            )}

            {/* Toolbar */}
            {!isSubmitted && (
                <div className="card rounded-t-xl border-b-0 p-3 flex items-center gap-2 flex-wrap">
                    <button
                        onClick={() => editor?.chain().focus().toggleBold().run()}
                        disabled={!editor?.can().chain().focus().toggleBold().run()}
                        className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${editor?.isActive("bold") ? "btn-accent" : "btn-outline-accent"
                            }`}
                    >
                        B
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleItalic().run()}
                        disabled={!editor?.can().chain().focus().toggleItalic().run()}
                        className={`px-3 py-1.5 rounded text-xs italic transition-colors ${editor?.isActive("italic") ? "btn-accent" : "btn-outline-accent"
                            }`}
                    >
                        I
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
                        className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${editor?.isActive("heading", { level: 1 })
                            ? "btn-accent"
                            : "btn-outline-accent"
                            }`}
                    >
                        H1
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
                        className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${editor?.isActive("heading", { level: 2 })
                            ? "btn-accent"
                            : "btn-outline-accent"
                            }`}
                    >
                        H2
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
                        className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${editor?.isActive("heading", { level: 3 })
                            ? "btn-accent"
                            : "btn-outline-accent"
                            }`}
                    >
                        H3
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleBulletList().run()}
                        className={`px-3 py-1.5 rounded text-xs transition-colors ${editor?.isActive("bulletList") ? "btn-accent" : "btn-outline-accent"
                            }`}
                    >
                        • List
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleOrderedList().run()}
                        className={`px-3 py-1.5 rounded text-xs transition-colors ${editor?.isActive("orderedList") ? "btn-accent" : "btn-outline-accent"
                            }`}
                    >
                        1. List
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().toggleBlockquote().run()}
                        className={`px-3 py-1.5 rounded text-xs transition-colors ${editor?.isActive("blockquote") ? "btn-accent" : "btn-outline-accent"
                            }`}
                    >
                        " Quote
                    </button>

                    <div className="h-6 w-px mx-1" style={{ backgroundColor: "var(--border)" }} />

                    <button
                        onClick={() => editor?.chain().focus().undo().run()}
                        className="btn-outline-accent px-3 py-1.5 rounded text-xs transition-colors cursor-pointer"
                    >
                        ↩ Undo
                    </button>

                    <button
                        onClick={() => editor?.chain().focus().redo().run()}
                        className="btn-outline-accent px-3 py-1.5 rounded text-xs transition-colors cursor-pointer"
                    >
                        ↪ Redo
                    </button>

                    <button
                        onClick={saveProposal}
                        disabled={saving}
                        className="px-4 py-1.5 btn-outline-accent rounded text-xs disabled:opacity-50 transition-colors ml-auto"
                    >
                        {saving ? "Saving..." : saved ? "✓ Saved" : "Save Draft"}
                    </button>
                </div>
            )}

            {/* Editor area */}
            <div
                className={`card ${!isSubmitted ? "rounded-b-xl rounded-t-none border-t-0" : "rounded-xl"
                    }`}
                style={{ minHeight: "400px" }}
            >
                <EditorContent
                    editor={editor}
                    className="text-primary"
                    style={{ pointerEvents: isSubmitted ? "none" : "auto" }}
                />
            </div>

            {/* Submit button */}
            {!isSubmitted && (
                <div className="mt-6 flex items-center justify-between">
                    <p className="text-muted text-xs">
                        Save your edits before submitting. Once submitted you cannot edit further.
                    </p>
                    <button
                        onClick={submitProposal}
                        disabled={submitting}
                        className="btn-accent px-6 py-3 rounded-lg font-semibold text-sm disabled:opacity-50"
                    >
                        {submitting ? "Submitting..." : "Submit for Review →"}
                    </button>
                </div>
            )}

            {/* Toast notification */}
            <div
                className="fixed bottom-8 z-100 transition-all duration-300"
                style={{
                    left: "50%",
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