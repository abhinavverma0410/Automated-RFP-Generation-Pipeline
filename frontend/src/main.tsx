import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from "@clerk/clerk-react"
import './index.css'
import App from './App.tsx'

// Read publishable key from environment variables
// Vite exposes env variables prefixed with VITE_ via import.meta.env
const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!publishableKey) {
    throw new Error("VITE_CLERK_PUBLISHABLE_KEY is missing from .env file")
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* ClerkProvider wraps the entire app */}
    {/* It provides auth state to every component */}
    <ClerkProvider publishableKey={publishableKey} signInUrl="/sign-in" signUpUrl="/sign-up">
      <App />
    </ClerkProvider>
  </StrictMode>,
)