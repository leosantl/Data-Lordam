# Módulo `security` (Fase 0)

Primeiro bounded context implementado, cobrindo autenticação e um RBAC mínimo. Base viva para os demais módulos seguirem o mesmo padrão de Clean Architecture.

## Contrato

- `POST /auth/register` — cria usuário (`email`, `password`) → `201` com `UserResponse`, `409` se email já existe.
- `POST /auth/login` — autentica (`email`, `password`) → `200` com `TokenResponse` (JWT), `401` em credenciais inválidas.
- `GET /auth/me` — retorna o usuário autenticado a partir do header `Authorization: Bearer <token>` → `200` com `UserResponse`, `401` sem token/token inválido.

## Domínio

- `User` (agregado): `email` (VO `Email` do `shared_kernel`), `hashed_password`, `role` (`owner|editor|viewer|auditor`), `is_active`.
- RBAC mínimo: papel único por usuário (`Role`), sem tabela de permissões granular ainda — isso é hardening da Fase 10.
- Todo usuário novo nasce com `role=viewer`; promoção de papel é decisão de produto adiada (não implementada nesta fase).

## Eventos publicados

- `UserRegistered`, `UserAuthenticated`, `PermissionDenied` (este último ainda não é emitido por nenhum caso de uso desta fase — reservado para quando houver checagem de permissão por ação).

## Como rodar localmente

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export DATABASE_URL="postgresql+asyncpg://lordam:lordam@localhost:5432/lordam"
.venv/bin/alembic upgrade head
.venv/bin/uvicorn src.api.main:app --reload
```

## Testes

- `backend/tests/unit/...` — domínio e casos de uso isolados de I/O (fakes para repositório/hasher/token/event bus).
- `backend/tests/integration/test_auth_api.py` — fluxo real via API + Postgres (schema criado/dropado por sessão de teste, tabelas truncadas entre testes).

```bash
.venv/bin/pytest tests -v      # 21 testes, unit + integração
.venv/bin/ruff check src tests
.venv/bin/mypy src
```

## Limitações conhecidas

- Sem refresh token (só access token de curta duração) — a implementar quando o frontend precisar de sessões longas.
- Sem rate limiting em `/auth/login` — necessário antes de produção.
- RBAC é um único papel por usuário; permissões por projeto (`roles`/`permissions`/`user_roles` como desenhado em `docs/ARCHITECTURE.md` §7) ficam para a Fase 10.
- `JwtTokenProvider` não faz rotação de chave; `jwt_secret_key` é uma única chave de ambiente.
