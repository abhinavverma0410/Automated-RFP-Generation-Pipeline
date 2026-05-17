// A custom hook is a reusable function that contains React logic
// Convention: always starts with "use"
// This hook manages theme state and persists it to localStorage

import { useState, useEffect } from "react"

export function useTheme() {
    // Read saved theme from localStorage on first load
    // If nothing saved, default to "dark"
    const [theme, setTheme] = useState<"dark" | "light">(() => {
        const saved = localStorage.getItem("theme")
        // localStorage persists data across browser sessions
        // Returns null if key doesn't exist
        return (saved as "dark" | "light") || "dark"
    })

    useEffect(() => {
        const root = document.documentElement
        // document.documentElement = the <html> element
        // Adding/removing "light" class switches CSS variable sets

        if (theme === "light") {
            root.classList.add("light")
        } else {
            root.classList.remove("light")
        }

        // Save preference to localStorage so it persists on refresh
        localStorage.setItem("theme", theme)
    }, [theme])
    // Re-runs whenever theme changes

    const toggleTheme = () => {
        // Toggle between dark and light
        setTheme(prev => prev === "dark" ? "light" : "dark")
    }

    return { theme, toggleTheme }
    // Return both the current theme and the toggle function
    // Components that call useTheme() get access to both
}