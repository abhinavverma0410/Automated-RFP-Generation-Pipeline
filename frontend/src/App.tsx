import { BrowserRouter, Routes, Route } from "react-router-dom"
// BrowserRouter — wraps the entire app and enables URL-based routing
// Routes       — container for all Route definitions
// Route        — maps a URL path to a component

import { SignedIn, SignedOut, RedirectToSignIn } from "@clerk/clerk-react"
// SignedIn     — renders children only if user is logged in
// SignedOut    — renders children only if user is logged out
// RedirectToSignIn — redirects to Clerk's sign in page

import Navbar from "./components/Navbar"
import Dashboard from "./pages/Dashboard"
import TenderDetail from "./pages/TenderDetail"
import Proposals from "./pages/Proposals"
import ProposalEditor from "./pages/ProposalEditor"
import AdminPanel from "./pages/AdminPanel"

import SignInPage from "./pages/SignInPage"
import SignUpPage from "./pages/SignUpPage"

export default function App() {
    return (
        <BrowserRouter>
            <div
                className="min-h-screen"
                style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}
            >
                <Routes>

                    {/* Sign In page */}
                    <Route path="/sign-in/*" element={<SignInPage />} />

                    {/* Sign Up page */}
                    <Route path="/sign-up/*" element={<SignUpPage />} />

                    {/* Protected routes — require sign in */}
                    <Route
                        path="/*"
                        element={
                            <>
                                <SignedIn>
                                    {/* Navbar only shows when signed in */}
                                    <Navbar />
                                    <main className="pt-16">
                                        <Routes>
                                            <Route path="/" element={<Dashboard />} />
                                            <Route path="/tenders/:reference_number" element={<TenderDetail />} />
                                            <Route path="/proposals" element={<Proposals />} />
                                            <Route path="/proposals/:reference_number/edit" element={<ProposalEditor />} />
                                            <Route path="/admin" element={<AdminPanel />} />
                                        </Routes>
                                    </main>
                                </SignedIn>
                                <SignedOut>
                                    {/* Redirect to sign in if not authenticated */}
                                    <RedirectToSignIn />
                                </SignedOut>
                            </>
                        }
                    />
                </Routes>
            </div>
        </BrowserRouter>
    )
}