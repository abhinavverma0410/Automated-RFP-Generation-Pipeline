import { SignUp } from "@clerk/clerk-react"
import { useTheme } from "../hooks/useTheme"

export default function SignUpPage() {
    const { theme, toggleTheme } = useTheme()

    return (
        <div
            className="min-h-screen flex items-center justify-center p-4"
            style={{ backgroundColor: "var(--bg-primary)" }}
        >
            {/* Theme toggle — top right corner */}
            <button
                onClick={toggleTheme}
                className="fixed top-4 right-4 w-9 h-9 rounded-lg border flex items-center justify-center transition-colors text-lg"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--nav-hover)")}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = "var(--bg-card)")}
                title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
                {theme === "dark" ? "☀️" : "🌙"}
            </button>

            <SignUp
                routing="path"
                path="/sign-up"
                forceRedirectUrl="/"
                appearance={{
                    variables: {
                        colorPrimary: theme === "dark" ? "#9d4edd" : "#0ea5e9",
                        // Changes Continue button color based on current theme
                        colorBackground: "var(--bg-secondary)",
                        colorText: "var(--text-primary)",
                        colorTextSecondary: "var(--text-secondary)",
                        colorInputBackground: "var(--bg-card)",
                        colorInputText: "var(--text-primary)",
                        colorShimmer: theme === "dark" ? "#9d4edd" : "#0ea5e9",
                        borderRadius: "0.5rem",
                        fontFamily: "inherit",
                    },
                    elements: {
                        card: "shadow-2xl border border-theme",
                        formButtonPrimary: "btn-accent",

                        // Sign up / Sign in hyperlink color
                        footerActionLink: {
                            color: theme === "dark" ? "#9d4edd" : "#0ea5e9",
                        },

                        // Google/Apple/Microsoft button text and icon color in dark mode
                        socialButtonsBlockButton: {
                            color: theme === "dark" ? "#ffffff" : undefined,
                            borderColor: "var(--border)",
                            backgroundColor: "var(--bg-card)",
                        },

                        socialButtonsBlockButtonText: {
                            color: theme === "dark" ? "#ffffff" : undefined,
                        },

                        // Apple logo specifically
                        socialButtonsProviderIcon__apple: {
                            filter: theme === "dark" ? "invert(1)" : undefined,
                            // invert(1) turns black logo white in dark mode
                        },
                    }
                }}
            />
        </div>
    )
}