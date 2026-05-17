import { Link, NavLink } from "react-router-dom"
import { useUser } from "@clerk/clerk-react"
import { UserButton } from "@clerk/clerk-react"
// UserButton — Clerk's pre-built user avatar button
// Shows profile picture, clicking opens a dropdown with sign out option
import { useTheme } from "../hooks/useTheme"

export default function Navbar() {
    const { theme, toggleTheme } = useTheme()
    const { user } = useUser()

    const ADMIN_USER_ID = "user_3DUETmR7WUiWa8jEvf1S5YcgkrF" // ← same ID as AdminPanel


    return (
        <nav className="nav-surface fixed top-0 left-0 right-0 z-50 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

                <Link to="/" className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded flex items-center justify-center btn-accent">
                        <span className="font-black text-sm text-white">R</span>
                    </div>
                    <div>
                        <span className="text-primary font-bold text-sm tracking-wide block">
                            RFP Pipeline
                        </span>
                        <span className="text-muted text-xs block leading-none">
                            Government Tenders
                        </span>
                    </div>
                </Link>

                <div className="flex items-center gap-1">
                    <NavLink
                        to="/"
                        className={({ isActive }) =>
                            `px-4 py-2 rounded text-sm font-medium transition-colors ${isActive ? "btn-outline-accent" : "text-secondary hover:bg-(--nav-hover)"
                            }`
                        }
                    >
                        Tenders
                    </NavLink>

                    <NavLink
                        to="/proposals"
                        className={({ isActive }) =>
                            `px-4 py-2 rounded text-sm font-medium transition-colors ${isActive ? "btn-outline-accent" : "text-secondary hover:bg-(--nav-hover)"
                            }`
                        }
                    >
                        Proposals
                    </NavLink>

                    {/* Admin link — only visible to admin user */}
                    {user?.id === ADMIN_USER_ID && (
                        <NavLink
                            to="/admin"
                            className={({ isActive }) =>
                                `px-4 py-2 rounded text-sm font-medium transition-colors ${isActive ? "btn-outline-accent" : "text-secondary hover:bg-(--nav-hover)"
                                }`
                            }
                        >
                            Admin
                        </NavLink>
                    )}
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={toggleTheme}
                        className="w-9 h-9 rounded-lg border-theme border flex items-center justify-center transition-colors text-lg"
                        style={{ borderColor: "var(--border)" }}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--nav-hover)")}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                    >
                        {theme === "dark" ? "☀️" : "🌙"}
                    </button>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                        <span className="text-muted text-xs">Live</span>
                    </div>
                    {/* User avatar + sign out dropdown */}
                    <UserButton />
                </div>
            </div>
        </nav>
    )
}