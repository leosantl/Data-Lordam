import { apiClient } from '@/lib/api-client'

export type Role = 'owner' | 'editor' | 'viewer' | 'auditor'

export interface User {
  id: string
  email: string
  role: Role
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  register: (email: string, password: string) =>
    apiClient.post<User>('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),
  me: (token: string) => apiClient.get<User>('/auth/me', token),
}
