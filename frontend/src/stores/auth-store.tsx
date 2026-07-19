import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

const TOKEN_STORAGE_KEY = 'lordam.access_token'

interface AuthContextValue {
  token: string | null
  setToken: (token: string | null) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_STORAGE_KEY),
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      setToken: (next) => {
        if (next) {
          localStorage.setItem(TOKEN_STORAGE_KEY, next)
        } else {
          localStorage.removeItem(TOKEN_STORAGE_KEY)
        }
        setTokenState(next)
      },
      signOut: () => {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        setTokenState(null)
      },
    }),
    [token],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
