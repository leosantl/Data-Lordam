import { useQuery } from '@tanstack/react-query'
import { authApi } from '@/features/auth/api/auth-api'
import { useAuth } from '@/stores/auth-store'
import { Button } from '@/components/ui/Button'

export function DashboardPage() {
  const { token, signOut } = useAuth()

  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'me', token],
    queryFn: () => authApi.me(token!),
    enabled: !!token,
  })

  return (
    <div className="min-h-svh bg-neutral-50 p-8 dark:bg-neutral-950">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Lordam Data Engine
        </h1>
        <Button onClick={signOut} className="bg-neutral-800 hover:bg-neutral-700">
          Sair
        </Button>
      </header>

      <section className="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
        {isLoading && <p className="text-neutral-500">Carregando...</p>}
        {user && (
          <p className="text-neutral-700 dark:text-neutral-300">
            Logado como <strong>{user.email}</strong> ({user.role})
          </p>
        )}
        <p className="mt-4 text-sm text-neutral-500">
          Fase 0 concluída: autenticação funcionando ponta a ponta. Os módulos de
          importação, limpeza e cruzamento de dados chegam nas próximas fases.
        </p>
      </section>
    </div>
  )
}
