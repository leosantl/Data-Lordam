# Lordam Data Engine — Plano de Arquitetura

> Status: **Proposta de arquitetura (pré-implementação)**
> Este documento é o ponto de partida do projeto. Nenhum código de produto foi escrito ainda — o objetivo aqui é fixar contratos, limites de módulo, modelo de dados, riscos e a ordem de construção antes que a primeira linha de backend/frontend seja escrita, conforme pedido no briefing original.

## Índice

1. [Visão e escopo](#1-visão-e-escopo)
2. [Princípios arquiteturais](#2-princípios-arquiteturais)
3. [Visão de alto nível](#3-visão-de-alto-nível)
4. [Bounded contexts (DDD)](#4-bounded-contexts-ddd)
5. [Estrutura de diretórios](#5-estrutura-de-diretórios)
6. [Stack tecnológica e justificativas](#6-stack-tecnológica-e-justificativas)
7. [Modelo de dados (PostgreSQL)](#7-modelo-de-dados-postgresql)
8. [Motor de execução ETL/ELT](#8-motor-de-execução-etletl)
9. [Motor de IA / comandos em linguagem natural](#9-motor-de-ia--comandos-em-linguagem-natural)
10. [Motor de regras](#10-motor-de-regras)
11. [Cruzamento de dados (Join/Match Engine)](#11-cruzamento-de-dados-joinmatch-engine)
12. [Performance e escala](#12-performance-e-escala)
13. [Segurança e conformidade](#13-segurança-e-conformidade)
14. [Integração Power BI](#14-integração-power-bi)
15. [Observabilidade, auditoria e histórico](#15-observabilidade-auditoria-e-histórico)
16. [Estratégia de testes](#16-estratégia-de-testes)
17. [CI/CD e infraestrutura](#17-cicd-e-infraestrutura)
18. [Decisões técnicas (ADRs resumidas)](#18-decisões-técnicas-adrs-resumidas)
19. [Riscos e mitigação](#19-riscos-e-mitigação)
20. [Roadmap e ordem de desenvolvimento](#20-roadmap-e-ordem-de-desenvolvimento)
21. [Definition of Done por módulo](#21-definition-of-done-por-módulo)
22. [Glossário](#22-glossário)

---

## 1. Visão e escopo

O Lordam Data Engine substitui processos manuais de tratamento de dados (Excel, Power Query, scripts soltos) por uma plataforma única onde o usuário:

- conecta a dezenas de fontes (arquivos, bancos, APIs, nuvem, Google, Microsoft);
- importa, limpa, cruza e transforma milhões de linhas com performance previsível;
- comanda o sistema por linguagem natural ("remova duplicados", "cruze clientes com vendas por CNPJ", "atualize o Power BI");
- obtém indicadores, insights, previsões e relatórios automaticamente;
- audita tudo o que foi executado, por quem, quando e com qual resultado.

**Fora de escopo desta fase de planejamento:** qualquer implementação de código. Este documento define o que será construído e em que ordem; a implementação é tratada módulo a módulo em fases subsequentes (seção 20), cada uma com seu próprio ciclo de design detalhado, código, testes e documentação técnica.

**Não-objetivos permanentes:** o sistema não é um substituto de data warehouse gerenciado (não compete com Snowflake/BigQuery como motor de armazenamento primário) — ele orquestra, transforma e federa dados, usando DuckDB/Arrow como motor analítico embarcado e Postgres como metastore/plataforma, delegando armazenamento massivo bruto às fontes/cloud storage originais sempre que possível.

## 2. Princípios arquiteturais

| Princípio | Como se manifesta no Lordam Data Engine |
|---|---|
| Clean Architecture | Cada módulo de negócio tem `domain/ → application/ → infrastructure/ → interface/`, com dependências apontando sempre para dentro (domain não conhece framework, banco ou HTTP). |
| SOLID | Interfaces (`Protocol`/ABC) para cada porta de infraestrutura (`FileReader`, `DatabaseConnector`, `LLMProvider`, `PowerBIClient`...); implementações trocáveis via injeção de dependência. |
| DDD | Bounded contexts explícitos (seção 4), linguagem ubíqua documentada por contexto, agregados com invariantes (ex.: `Dataset`, `Pipeline`, `Rule`, `JoinSpec`). |
| Event-Driven | Toda transição relevante (`DatasetImported`, `CleaningApplied`, `JoinCompleted`, `PipelineFailed`, `RefreshRequested`) publica um evento de domínio em um *event bus* interno (Redis Streams), consumido por auditoria, monitoramento, workflow e notificações — desacoplando efeitos colaterais da lógica principal. |
| Modularização | Módulos independentes, comunicando-se por contratos (DTOs/eventos), nunca por import direto de `infrastructure` cruzado. Cada módulo pode evoluir/ser testado isoladamente. |
| Escalabilidade | Motor de dados columnar (Polars/DuckDB/Arrow) + processamento assíncrono (Celery/Redis) + streaming/chunking para datasets que não cabem em memória. |
| Segurança | Autenticação (JWT/OAuth2), autorização (RBAC por projeto), segredos cifrados (AES-256-GCM), trilha de auditoria imutável, conformidade LGPD (minimização, direito ao esquecimento, mascaramento de PII). |
| Performance | Benchmarks de aceite por volume (100k/500k/1M/5M/10M linhas) definidos por módulo antes de ir a produção. |
| Auditoria | Nenhuma operação que altera dados roda sem registro: usuário, timestamp, input, output, diff, duração, status. |

## 3. Visão de alto nível

```
                         ┌─────────────────────────┐
                         │        Frontend          │
                         │  React + TS + Tailwind   │
                         │  (Command Bar, ETL Flow, │
                         │   Dashboards, Monitor)   │
                         └────────────┬─────────────┘
                                      │ REST/WebSocket (TanStack Query)
                         ┌────────────▼─────────────┐
                         │        API Gateway        │
                         │   FastAPI (composition     │
                         │   root, auth, rate-limit)  │
                         └────────────┬─────────────┘
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
   ┌──────────▼─────────┐  ┌─────────▼──────────┐  ┌──────────▼─────────┐
   │   AI Copilot        │  │  Application Layer  │  │   Workflow Engine   │
   │  (NLU → Command      │  │  (casos de uso por  │  │  (scheduler, DAG    │
   │   Plan → Confirm)     │  │   módulo de negócio)│  │   de pipelines)     │
   └──────────┬─────────┘  └─────────┬──────────┘  └──────────┬─────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │ Domain Events (Redis Streams)
                         ┌────────────▼─────────────┐
                         │      Data Engine Core      │
                         │  Polars / DuckDB / Arrow   │
                         │  (ingestion, cleaning,     │
                         │   matching, transform)      │
                         └────────────┬─────────────┘
              ┌───────────────────────┼───────────────────────┐
   ┌──────────▼─────────┐  ┌─────────▼──────────┐  ┌──────────▼─────────┐
   │     Connectors       │  │   Metastore (Postgres)│  │   Object/Cache     │
   │ Files/DB/API/Cloud/  │  │  users, projects,     │  │  Storage + Redis   │
   │ Google/Microsoft     │  │  datasets, workflows,  │  │  (staging, cache,  │
   │                       │  │  audit, rules, insights│  │   Celery broker)   │
   └──────────────────────┘  └────────────────────┘  └────────────────────┘
```

Workers assíncronos (Celery) executam pipelines, jobs de ML, refresh de Power BI e geração de relatórios fora do request-response, reportando progresso via WebSocket/eventos.

## 4. Bounded contexts (DDD)

Cada contexto é um módulo autônomo, com seu próprio modelo de domínio e linguagem ubíqua. Comunicação entre contextos é feita por **eventos de domínio** ou **application services** publicados como *ports*, nunca por acesso direto a tabelas de outro contexto.

| Contexto | Responsabilidade | Agregado raiz | Eventos publicados |
|---|---|---|---|
| **Ingestion** (conectores) | Detectar schema/encoding, importar de qualquer fonte, gerar preview | `ImportJob`, `Connection` | `DatasetImported`, `ImportFailed` |
| **Cleaning** (limpeza) | Funções de padronização/correção em massa | `CleaningOperation` | `CleaningApplied` |
| **Transformation** (ETL/ELT) | Pipelines de transformação, operações em massa por coluna | `Pipeline`, `Dataset` | `PipelineStarted`, `PipelineCompleted`, `PipelineFailed` |
| **Rules Engine** | Regras condicionais SE/ENTÃO reutilizáveis | `Rule`, `RuleSet` | `RuleEvaluated`, `RuleTriggered` |
| **Matching** (cruzamento) | Joins determinísticos e fuzzy match | `JoinSpec`, `MatchResult` | `JoinCompleted`, `MatchAmbiguityDetected` |
| **AI Copilot** | Interpretar linguagem natural, planejar e orquestrar ações nos demais contextos | `CommandIntent`, `ExecutionPlan` | `CommandInterpreted`, `PlanExecuted`, `PlanRejected` |
| **Data Quality / Profiling** | Detecção de erros, estatísticas, perfilamento | `DataQualityReport` | `AnomalyDetected`, `ProfileGenerated` |
| **ML / Insights** | Clusterização, forecast, scoring, detecção de fraude, geração de insights | `MLModel`, `InsightReport` | `ModelTrained`, `InsightGenerated` |
| **Power BI Integration** | Publicação e refresh de datasets/relatórios | `PowerBIWorkspace`, `RefreshJob` | `RefreshRequested`, `RefreshCompleted`, `RefreshFailed` |
| **Workflow / Scheduler** | Orquestração de pipelines multi-step, agendamento | `Workflow`, `WorkflowRun` | `WorkflowTriggered`, `WorkflowStepFailed` |
| **Reports** | Geração de PDF/Excel/Word/PPT/HTML/Markdown | `ReportTemplate`, `ReportRun` | `ReportGenerated` |
| **Monitoring / Dashboard interno** | Métricas de execução, uso de CPU/memória, saúde do sistema | `SystemMetric` | — (consumidor de eventos) |
| **Audit / History** | Log imutável de todas as operações, suporte a rollback | `AuditEntry` | — (consumidor de eventos) |
| **Security / IAM** | Autenticação, RBAC, criptografia de credenciais, LGPD | `User`, `Role`, `Permission`, `Credential` | `UserAuthenticated`, `PermissionDenied` |

O contexto **AI Copilot** é o único que depende diretamente dos application services de todos os outros — ele é uma camada de orquestração, não de negócio: traduz intenção em uma sequência de casos de uso já existentes (nunca reimplementa lógica de limpeza/join/etc.). Isso garante que qualquer ação disponível via UI também está disponível via linguagem natural, e vice-versa, sem duplicação de regra de negócio.

## 5. Estrutura de diretórios

A árvore abaixo elabora a proposta original (`core/ engine/ etl/ transform/ ai/ ...`) aplicando Clean Architecture dentro de cada bounded context, para evitar que "engine", "etl" e "transform" colidam em responsabilidade:

```
lordam-data-engine/
├── backend/
│   ├── src/
│   │   ├── core/                     # config, DI container, base entities/VOs, exceptions, logging, event bus
│   │   ├── shared_kernel/            # VOs compartilhados: CPF, CNPJ, Email, Money, DateRange...
│   │   ├── modules/
│   │   │   ├── ingestion/
│   │   │   │   ├── domain/           # entidades, VOs, regras de negócio puras
│   │   │   │   ├── application/      # casos de uso (ImportFile, DetectSchema, PreviewImport)
│   │   │   │   ├── infrastructure/   # conectores concretos (csv_reader, xlsx_reader, postgres_connector...)
│   │   │   │   └── interface/        # routers FastAPI, schemas Pydantic
│   │   │   ├── cleaning/
│   │   │   ├── transformation/
│   │   │   ├── rules_engine/
│   │   │   ├── matching/
│   │   │   ├── ai_copilot/
│   │   │   ├── data_quality/
│   │   │   ├── ml_insights/
│   │   │   ├── powerbi/
│   │   │   ├── workflow/
│   │   │   ├── reports/
│   │   │   ├── monitoring/
│   │   │   ├── audit/
│   │   │   └── security/
│   │   ├── api/                      # composition root FastAPI, montagem de routers, middlewares
│   │   ├── infrastructure/           # infra compartilhada: db session, redis client, celery app, storage, arrow/duckdb engine
│   │   └── workers/                  # tasks Celery (pipelines, refresh, relatórios, ML)
│   ├── tests/
│   │   ├── unit/                     # espelha modules/*/domain e application
│   │   ├── integration/              # infra real (Postgres/Redis via testcontainers)
│   │   └── e2e/                      # fluxo API completo
│   ├── alembic/                      # migrations do metastore Postgres
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                      # rotas, layout raiz
│   │   ├── features/                 # espelha os módulos do backend (command-bar, etl-flow, rules, connectors...)
│   │   ├── components/               # design system (shadcn/ui based)
│   │   ├── hooks/
│   │   ├── lib/                      # api client, query keys
│   │   └── stores/
│   ├── package.json
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml            # postgres, redis, backend, worker, frontend, nginx
│   ├── nginx/
│   └── github-actions/               # workflows de CI/CD
├── docs/
│   ├── ARCHITECTURE.md               # este documento
│   ├── adr/                          # Architecture Decision Records individuais
│   └── modules/                      # doc técnica por módulo (criada junto com cada módulo)
└── README.md
```

**Regra de dependência entre módulos:** `domain` não importa nada de `application/infrastructure/interface`. `application` importa `domain` e depende de **interfaces** de infraestrutura (não de implementações). `infrastructure` implementa essas interfaces. `interface` (routers) depende só de `application`. Módulos de negócio nunca importam `infrastructure` de outro módulo — a comunicação cross-module é via `application services` expostos ou eventos.

## 6. Stack tecnológica e justificativas

| Camada | Tecnologia | Por quê |
|---|---|---|
| Motor de dados | **Polars** (primário) | Execução paralela, lazy evaluation, baixo overhead de memória; API expressiva para pipelines declarativos. |
| Motor analítico/SQL | **DuckDB** | SQL embarcado sobre Arrow/Parquet, ideal para joins/agregações pesadas e para consultas ad-hoc geradas pela IA. |
| Formato in-memory/interop | **Apache Arrow / PyArrow** | Interoperabilidade zero-copy entre Polars, DuckDB, Pandas e conectores externos. |
| Compatibilidade | **Pandas** (só quando exigido) | Usado apenas em conectores/bibliotecas de terceiros que não suportam Arrow/Polars nativamente (ex.: alguma lib de ML legada). Nunca como motor principal de transformação. |
| API | **FastAPI + Pydantic v2** | Tipagem, validação automática, async nativo, geração de OpenAPI para o frontend e para o próprio AI Copilot (function calling). |
| ORM/Migrations | **SQLAlchemy 2.0 (async) + Alembic** | Metastore relacional tipado e versionado. |
| Metastore | **PostgreSQL 16** | Transacional, JSONB para metadados flexíveis (schemas detectados, parâmetros de regra), extensível (pgvector futuro para embeddings de matching semântico). |
| Fila/cache/broker | **Redis** | Broker do Celery, cache de resultados intermediários, pub/sub para progresso em tempo real. |
| Processamento assíncrono | **Celery** | Pipelines longos, refresh de Power BI, treinamento de ML, geração de relatórios — fora do ciclo request/response. |
| IA / LLM | **Provider-agnostic** via porta `LLMProvider` (Claude, OpenAI, Gemini, Ollama local) | Evita lock-in; permite failover e uso de modelo local para dados sensíveis (LGPD). |
| Frontend | **React + TypeScript + TailwindCSS + shadcn/ui** | Produtividade, tipagem ponta a ponta, componentes acessíveis. |
| Data fetching | **TanStack Query** | Cache, invalidação, polling de status de jobs assíncronos. |
| Editor visual de ETL | **React Flow** | Grafo de pipeline (nós de import/clean/join/rule/output). |
| Editor de regras/scripts | **Monaco Editor** | Edição de expressões de regra e SQL avançado quando o usuário quiser ir além da IA. |
| Gráficos | **Recharts** | Dashboards internos e preview de indicadores. |
| Infraestrutura | **Docker Compose** (dev/staging), pronto para orquestração Kubernetes em produção corporativa | Paridade de ambiente, onboarding rápido. |
| CI/CD | **GitHub Actions** | Lint, type-check, testes, build de imagens, scans de segurança. |

## 7. Modelo de dados (PostgreSQL)

O Postgres é o **metastore** (metadados, controle, auditoria) — não armazena os dados de negócio em massa (esses vivem em Parquet/staging em object storage e são processados via Arrow/DuckDB sob demanda). Tabelas principais (nomes indicativos, refinados em migrations reais):

| Tabela | Propósito | Campos-chave |
|---|---|---|
| `users` | Contas de usuário | id, email, password_hash, mfa_enabled, status |
| `roles` / `permissions` / `user_roles` | RBAC | role_id, permission_key, scope (global/project) |
| `projects` | Espaço de trabalho isolado (multi-tenant lógico) | id, name, owner_id, settings |
| `connections` | Conexões configuradas com fontes | id, project_id, type, config_json (não-sensível) |
| `credentials` | Segredos de conexão | id, connection_id, ciphertext (AES-256-GCM), key_version |
| `datasets` | Metadados de datasets importados/gerados | id, project_id, source, schema_json, row_count, storage_path, checksum |
| `transformations` | Operações de limpeza/transformação aplicadas | id, dataset_id, type, params_json, order |
| `rules` | Regras do Rule Engine | id, project_id, condition_json, action_json, enabled |
| `join_specs` | Configurações de cruzamento salvas | id, project_id, left_dataset_id, right_dataset_id, keys, join_type, fuzzy_threshold |
| `workflows` | Definição de pipelines/DAGs | id, project_id, definition_json (nós e arestas) |
| `workflow_runs` | Execuções de workflow | id, workflow_id, status, started_at, finished_at, triggered_by |
| `executions` | Execuções granulares (um step) | id, workflow_run_id, module, status, duration_ms, rows_in, rows_out, error |
| `logs` | Log estruturado de execução | id, execution_id, level, message, payload_json |
| `audit_entries` | Trilha de auditoria imutável | id, user_id, action, entity, entity_id, diff_json, created_at |
| `insights` | Insights gerados pela IA/ML | id, project_id, dataset_id, type, summary, payload_json, confidence |
| `ml_models` | Modelos treinados e metadados | id, project_id, type, metrics_json, artifact_path, version |
| `dashboards` | Definições de dashboard interno | id, project_id, layout_json |
| `favorites` | Atalhos do usuário (datasets, pipelines, dashboards) | id, user_id, entity_type, entity_id |
| `powerbi_workspaces` | Vínculo com workspaces do Power BI | id, project_id, workspace_id, dataset_id |
| `refresh_jobs` | Histórico de refresh do Power BI | id, powerbi_workspaces_id, status, triggered_by |
| `reports` | Relatórios gerados | id, project_id, format, storage_path, generated_by |
| `ai_commands` | Histórico de comandos em linguagem natural | id, user_id, project_id, raw_text, interpreted_plan_json, status |

Todas as tabelas de execução carregam `created_at`/`updated_at` e `created_by`; nenhuma exclusão física de histórico — apenas soft delete onde aplicável (LGPD tratada via campo de anonimização, não via `DELETE` de auditoria).

## 8. Motor de execução ETL/ELT

Um **Pipeline** é um grafo acíclico dirigido de **Steps** tipados (`ImportStep`, `CleaningStep`, `RuleStep`, `JoinStep`, `TransformStep`, `OutputStep`). Cada step:

1. Recebe um ou mais `DatasetRef` (ponteiro lazy para dados em Arrow/Parquet, não os dados materializados);
2. Aplica uma operação Polars/DuckDB lazy (`LazyFrame`);
3. Emite métricas (linhas de entrada/saída, duração, avisos de qualidade);
4. Publica um evento de domínio ao concluir.

**ELT vs ETL:** para fontes que suportam pushdown (Postgres, BigQuery, Snowflake), o motor prefere gerar SQL e empurrar a transformação para a fonte (ELT); para arquivos e fontes sem pushdown, o processamento roda no motor Polars/DuckDB local (ETL). Essa decisão é feita pelo `Planner` do pipeline por step, não é uma escolha global do sistema.

**Execução:** pipelines pequenos/rápidos (preview, < 100k linhas) rodam de forma síncrona dentro do request; pipelines completos rodam como task Celery, com progresso reportado via WebSocket (`workflow_runs`/`executions` atualizados a cada step).

## 9. Motor de IA / comandos em linguagem natural

Fluxo de um comando (ex.: *"Cruze Financeiro com CRM por CPF, remova inválidos e publique no Power BI"*):

1. **Contexto**: o Copilot recebe o comando + metadados do projeto (datasets disponíveis, colunas, schemas, workflows existentes) — nunca os dados brutos linha a linha, apenas schema/estatísticas, por custo e por LGPD.
2. **Interpretação**: o LLM (via `LLMProvider` com *function calling*/tool-use) mapeia o texto para uma sequência de **ações tipadas já existentes** nos application services dos módulos (`ImportDataset`, `ApplyCleaning`, `JoinDatasets`, `PublishToPowerBI`...). O LLM nunca gera SQL/código arbitrário para execução direta — ele só seleciona e parametriza casos de uso pré-existentes, o que limita a superfície de risco.
3. **Plano (`ExecutionPlan`)**: é serializado, mostrado ao usuário em linguagem natural + preview estruturado ("vou fazer X, Y, Z, afetando N linhas") **antes** de executar.
4. **Confirmação**: ações destrutivas ou que afetam sistemas externos (excluir dados, publicar no Power BI, enviar e-mail) exigem confirmação explícita do usuário; ações somente-leitura (perfilamento, insight) executam direto.
5. **Execução**: o plano vira um `Workflow` (mesma engine da seção 8), garantindo que o resultado de um comando de IA é auditável e reexecutável como qualquer outro pipeline.
6. **Resposta**: resumo em linguagem natural + link para o resultado (dataset, dashboard, relatório).

Isso mantém a IA como uma **camada de orquestração sobre casos de uso determinísticos e testáveis**, não como um gerador de código solto — essencial tanto para segurança quanto para auditabilidade.

## 10. Motor de regras

`Rule = Condition (árvore de expressões: campo, operador, valor, AND/OR) + Action (excluir, marcar, criar coluna, transformar)`. Regras são armazenadas como JSON serializável (não código), avaliadas por um interpretador próprio compilado para expressão Polars (`pl.when(...).then(...)`), evitando `eval()`/execução de código arbitrário do usuário. Reutilizáveis entre pipelines, versionadas, com histórico de alterações via `audit_entries`.

## 11. Cruzamento de dados (Join/Match Engine)

- Joins determinísticos (`INNER/LEFT/RIGHT/FULL/SELF`) delegados ao DuckDB (mais eficiente que hash-join manual para grandes volumes).
- Fuzzy match (nome, endereço) usa normalização (unaccent, lowercase, remoção de stopwords) + similaridade (Jaro-Winkler/Levenshtein via `rapidfuzz`) com **threshold configurável** e **blocking** (pré-agrupamento por chave determinística, ex. mesmo CEP/DDD) para evitar comparação O(n×m) em milhões de linhas.
- Chaves de negócio (CPF/CNPJ/e-mail/telefone) passam por normalização de domínio própria (Value Objects do `shared_kernel`) antes de qualquer comparação.
- Resultado de match ambíguo (múltiplos candidatos acima do threshold) gera `MatchAmbiguityDetected` para revisão humana, nunca resolve silenciosamente.

## 12. Performance e escala

- **Lazy by default**: toda a pipeline usa `LazyFrame` (Polars) / lazy SQL (DuckDB); materialização só no último step ou quando exigida por preview.
- **Streaming/chunking**: leitura de arquivos grandes em batches (Arrow record batches), sem carregar arquivo inteiro em memória.
- **Processamento incremental**: datasets versionados por `checksum`/`watermark` de coluna (ex. `updated_at`), permitindo reprocessar apenas deltas em workflows agendados.
- **Paralelismo**: Polars usa todos os cores automaticamente; jobs independentes de um workflow rodam em paralelo via Celery (grafo de dependência determina o que pode paralelizar).
- **Cache inteligente**: resultados intermediários de steps determinísticos cacheados em Parquet/Redis com chave = hash(step + inputs); reaproveitado em reexecuções e previews.
- **Metas de aceite por volume** (a validar em benchmark real antes de cada release): 100k linhas < 2s import+clean; 1M linhas < 20s; 10M linhas processável em modo streaming sem estourar memória de um worker de 4 vCPU/8GB — números-alvo, não garantias, e serão recalibrados com benchmarks reais no módulo correspondente.

## 13. Segurança e conformidade

- **AuthN**: JWT (access + refresh) sobre OAuth2 password/authorization-code flow; suporte a SSO (OIDC) corporativo como extensão futura.
- **AuthZ**: RBAC com permissões por projeto (`owner/editor/viewer/auditor`), checado na camada `application` (não só na UI).
- **Segredos**: credenciais de conexão cifradas em repouso com AES-256-GCM, chave gerenciada fora do banco (variável de ambiente/HSM/secret manager conforme ambiente), nunca logadas.
- **LGPD**: classificação de campos sensíveis (CPF, e-mail, telefone) no data profiling; suporte a mascaramento/anonimização em preview e exports; direito ao esquecimento implementado como fluxo de anonimização auditado (não exclusão de auditoria).
- **Auditoria**: todo endpoint que muda estado grava `audit_entries` com diff antes/depois; leitura de dados sensíveis também é logada quando o campo é marcado como PII.
- **Superfície de ataque da IA**: comandos em linguagem natural nunca resultam em execução de código arbitrário (seção 9) — mitiga prompt injection escalando para ações destrutivas sem confirmação.

## 14. Integração Power BI

- Autenticação via **Service Principal** (Azure AD app registration) — não credencial pessoal — para permitir refresh automatizado em workflows agendados.
- Client próprio (`PowerBIClient`, porta em `modules/powerbi/application`) sobre a **Power BI REST API**: publish de dataset, trigger de refresh, consulta de status, gestão de workspace.
- Refresh assíncrono via Celery com polling de status e evento `RefreshCompleted`/`RefreshFailed` alimentando notificações (Teams/e-mail).
- Fase avançada: exploração de **XMLA endpoint** (Premium/Fabric) para push incremental sem full refresh, quando o volume justificar.

## 15. Observabilidade, auditoria e histórico

- Métricas de sistema (CPU, memória, duração por step, throughput linhas/s) coletadas por worker e expostas no dashboard interno (`modules/monitoring`).
- Logs estruturados (JSON) correlacionados por `execution_id`/`workflow_run_id` (trace id propagado ponta a ponta).
- Toda execução é reexecutável a partir do histórico (`workflow_runs` guarda o `definition_json` versionado usado naquela run — não a versão atual do workflow, que pode ter mudado).
- Rollback: para operações que sobrescrevem um dataset, a versão anterior é preservada em storage (retenção configurável) e referenciável por `dataset_id + version`.

## 16. Estratégia de testes

| Nível | Escopo | Ferramentas |
|---|---|---|
| Unitário | `domain` e `application` de cada módulo, 100% isolado de I/O | `pytest`, fakes/in-memory para portas |
| Integração | `infrastructure` real contra Postgres/Redis/DuckDB (containers efêmeros) | `pytest` + `testcontainers` |
| Contrato | Schemas de API (Pydantic/OpenAPI) e eventos de domínio | `pytest` + `schemathesis` (fuzz de API) |
| Performance | Benchmarks por volume (seção 12) rodados em CI para PRs que tocam o motor de dados | `pytest-benchmark` |
| E2E backend | Fluxo completo via API (import → clean → join → publish) | `pytest` + client HTTP real contra stack docker-compose |
| Frontend | Componentes + fluxo de comando | `Vitest` + `Testing Library`, `Playwright` para E2E de UI |
| IA | Suite de comandos de referência com plano esperado (regressão do NLU) | dataset de golden prompts versionado |

Cobertura mínima de `domain`/`application` exigida por módulo antes de merge: 85%. `infrastructure` prioriza teste de contrato sobre cobertura numérica.

## 17. CI/CD e infraestrutura

- **GitHub Actions**: lint (`ruff`, `eslint`), type-check (`mypy`, `tsc`), testes unitários+integração, build de imagens Docker, scan de dependências/segredos, publish de imagem versionada.
- **Docker Compose** para dev/staging: `postgres`, `redis`, `backend`, `worker` (Celery), `frontend`, `nginx` (reverse proxy + TLS termination).
- Migrations (`alembic upgrade head`) rodam como *init container*/step de deploy, nunca automaticamente no boot da API em produção.
- Ambientes: `local` → `staging` → `production`, com feature flags para módulos ainda incompletos (ex. conectores cloud) desligados por padrão em produção até a fase correspondente do roadmap ser concluída.

## 18. Decisões técnicas (ADRs resumidas)

| # | Decisão | Alternativas consideradas | Motivo da escolha |
|---|---|---|---|
| ADR-001 | Polars+DuckDB+Arrow como motor primário, Pandas só de fallback | Pandas puro; Spark | Pandas não escala a 10M+ linhas com boa performance single-node; Spark é overkill operacional para a maioria dos clientes-alvo (adiciona cluster management) — reavaliar Spark/Dask apenas se surgir requisito de volumes >> memória de um único worker. |
| ADR-002 | Metastore Postgres + dados brutos em object storage/Parquet | Tudo em Postgres | Postgres não é motor colunar; misturar metadados com dados de negócio de milhões de linhas degradaria o metastore e acoplaria escala de metadado à escala de dado. |
| ADR-003 | IA restrita a orquestrar casos de uso existentes, sem gerar/executar código livre | LLM gera SQL/Python executado diretamente | Superfície de segurança muito menor, auditabilidade total, resultado sempre testável como os demais fluxos determinísticos do sistema. |
| ADR-004 | Arquitetura modular monolítica (não microsserviços) na v1 | Microsserviços por bounded context | Bounded contexts como módulos internos com fronteiras claras dão os benefícios de DDD sem o custo operacional de microsserviços distribuídos numa fase em que o time e a carga ainda não justificam isso; módulos são desenhados para poder ser extraídos depois (ports/adapters já isolam infraestrutura). |
| ADR-005 | Celery+Redis para assíncrono, não filas gerenciadas de cloud na v1 | AWS SQS, GCP Pub/Sub | Portabilidade entre ambientes on-prem/cloud dos clientes-alvo; Redis já é necessário para cache, reduz peças móveis. |
| ADR-006 | LLM provider-agnostic (Claude, OpenAI, Gemini, Ollama) | Lock-in em um único provider | Requisito de LGPD/dados sensíveis pode exigir modelo local (Ollama) por cliente; evita dependência de um único fornecedor. |

## 19. Riscos e mitigação

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| Escopo do projeto é extremamente amplo (dezenas de conectores, IA, ML, BI) | Alto — risco de nunca "terminar" ou entregar tudo raso | Alta | Roadmap faseado (seção 20) com fatias verticais completas e testadas antes de somar largura; cada fase entrega valor utilizável isoladamente. |
| Motor de fuzzy match/join em milhões de linhas sem blocking vira O(n²) | Alto — trava sistema em produção | Média | Blocking obrigatório antes de qualquer fuzzy match; limite configurável de candidatos por bloco; alertar usuário se estimativa de comparações exceder threshold antes de executar. |
| IA interpretando mal um comando e executando ação destrutiva | Alto — perda/corrupção de dados | Média | Plano de execução sempre mostrado e confirmado antes de ações destrutivas/externas (seção 9); toda execução fica em `workflow_runs` reexecutável/reversível quando possível. |
| Credenciais de dezenas de conectores mal geridas | Alto — vazamento de dados de clientes | Baixa/Média | Criptografia obrigatória (seção 13), nunca logar segredos, revisão de segurança dedicada por conector antes de habilitar em produção. |
| Custo/latência de LLM em comandos frequentes | Médio | Média | Cache de interpretação para comandos repetidos, opção de modelo local (Ollama) para operações de alto volume, plano síncrono só para leitura. |
| Integração Power BI depende de licenciamento/Premium para algumas features (XMLA) | Médio | Média | REST API padrão como baseline funcional para todos; XMLA tratado como enhancement opcional, não bloqueante. |
| Volume real de dados do cliente supera a capacidade de um único worker | Médio | Baixa (v1) | Arquitetura de worker stateless permite escalar horizontalmente (mais workers Celery); reavaliar necessidade de motor distribuído (Dask/Spark) só se isso se confirmar necessário. |
| Times de conectores para dezenas de fontes gera dívida de manutenção | Médio | Alta | Interface `Connector` única e testes de contrato; conectores adicionados incrementalmente por demanda real (seção 20), não todos de uma vez. |

## 20. Roadmap e ordem de desenvolvimento

Cada fase entrega uma **fatia vertical completa e testável** (não um módulo raso sem os demais). Fases são sequenciais na dependência técnica, mas o trabalho interno de cada fase pode paralelizar.

| Fase | Entrega | Depende de |
|---|---|---|
| **0 — Fundação** | Scaffold do monorepo (backend/frontend/infra), `core` (config, DI, exceptions, logging, event bus), `security` básico (auth JWT, RBAC mínimo), metastore Postgres com migrations iniciais, docker-compose funcional, CI com lint+testes | — |
| **1 — Import & Clean de arquivos** | Conectores de arquivo (CSV/Excel/JSON/Parquet), detecção automática de encoding/delimitador/tipos, preview, módulo `cleaning` com as operações essenciais (trim, duplicados, nulos, padronização de texto, CPF/CNPJ/data), tudo exposto via API + UI mínima (upload → preview → aplicar limpeza → baixar resultado) | Fase 0 |
| **2 — Motor de regras + Cruzamento** | `rules_engine` completo, `matching` com joins determinísticos (DuckDB) e fuzzy match com blocking, UI de configuração de join/regra | Fase 1 |
| **3 — Pipelines/Workflow + Auditoria** | `transformation` (pipeline como grafo de steps), `workflow` (encadeamento, agendamento simples), `audit` completo, editor visual (React Flow) | Fase 2 |
| **4 — AI Copilot (v1)** | NLU sobre os casos de uso já existentes das fases 1-3 (import, clean, rule, join, pipeline), plano de execução com confirmação, histórico de comandos | Fase 3 |
| **5 — Conectores de banco de dados** | PostgreSQL, MySQL/MariaDB, SQL Server, Oracle, SQLite via interface `Connector` comum, pushdown ELT quando aplicável | Fase 1 |
| **6 — Data Quality, Estatística e Profiling** | `data_quality` (detecção de erros, outliers, inconsistências), estatística descritiva, profiling automático, dashboard interno de qualidade | Fase 3 |
| **7 — Power BI + Relatórios** | `powerbi` (publish/refresh via REST API + Service Principal), `reports` (PDF/Excel/Word/HTML), envio por e-mail/Teams via workflow | Fase 3 (+ Fase 4 para "atualize meu Power BI" por comando) |
| **8 — ML & Insights avançados** | `ml_insights` (clusterização, forecast, detecção de anomalias/fraude, scoring), geração de insights automáticos em linguagem natural | Fase 6 |
| **9 — Conectores API/Cloud/Google/Microsoft** | REST/SOAP/GraphQL genéricos, OAuth2/API Key/Webhook, Google Sheets/Drive/BigQuery, SharePoint/OneDrive/Azure SQL/Fabric/Dataverse, AWS S3/Azure Blob/GCS/Snowflake/Databricks | Fase 5 |
| **10 — Hardening e LGPD avançado** | RBAC granular final, mascaramento de PII, direito ao esquecimento, criptografia de credenciais em produção, pentest interno | Contínuo a partir da Fase 0, formalizado antes de GA |
| **11 — Polimento de UI/UX e Dashboard executivo** | Dark/Light mode, dashboard principal, monitoramento em tempo real, favoritos/histórico completos na UI | Paralelo às fases 6-9 |

**Critério para avançar de fase:** a fase anterior precisa estar com testes passando, documentação técnica do(s) módulo(s) escrita e, quando aplicável, benchmark de performance validado — não apenas "código escrito".

## 21. Definition of Done por módulo

Um módulo só é considerado pronto quando tiver, simultaneamente:

- [ ] Domínio modelado com testes unitários (regras de negócio puras, sem I/O);
- [ ] Casos de uso (`application`) com testes cobrindo caminho feliz + erros de negócio;
- [ ] Ao menos um adaptador de infraestrutura real testado por integração;
- [ ] Endpoints de API documentados (OpenAPI) e validados por Pydantic;
- [ ] Eventos de domínio publicados e consumidos por auditoria/monitoramento;
- [ ] Documentação técnica em `docs/modules/<modulo>.md` (contrato, exemplos de uso, limitações conhecidas);
- [ ] Benchmark de performance quando o módulo processa dados de negócio em volume (import, cleaning, matching, transformation);
- [ ] Revisão de segurança quando o módulo lida com credenciais, PII ou execução de comando dinâmico (rules, AI copilot, conectores).

## 22. Glossário

- **Dataset**: unidade lógica de dados versionada e rastreável no sistema, com metadados no Postgres e conteúdo em Arrow/Parquet.
- **Pipeline**: sequência/grafo de steps de transformação aplicados a um ou mais datasets.
- **Workflow**: orquestração de nível superior que pode combinar múltiplos pipelines, agendamento e notificações.
- **Execution Plan**: sequência de ações tipadas gerada pelo AI Copilot a partir de um comando em linguagem natural, antes de virar um Workflow real.
- **Blocking** (em matching): técnica de pré-agrupamento de registros por uma chave barata antes de aplicar comparação fuzzy cara, para evitar complexidade quadrática.
- **Bounded Context**: fronteira de um subdomínio DDD com modelo e linguagem próprios.
- **Shared Kernel**: código de domínio (Value Objects) compartilhado deliberadamente entre módulos porque representa conceitos verdadeiramente universais (CPF, CNPJ, Email...).

---

### Próximos passos imediatos

1. Validar este documento com o time/stakeholders (nomes de tabelas, escopo de fases, stack).
2. Abrir a **Fase 0** como primeira issue/PR de implementação: scaffold do monorepo + `core` + `security` básico + metastore inicial + CI.
3. Criar `docs/adr/` com uma ADR formal por decisão da seção 18 à medida que forem implementadas (este resumo vira índice, não substitui as ADRs completas).
