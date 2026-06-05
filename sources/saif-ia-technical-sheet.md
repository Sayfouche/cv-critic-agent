# Fiche technique — SAIF-IA Chatbot
**Version :** Phases 1+2+3 livrées  
**Date :** 17 mai 2026  
**Stack :** Next.js 16 · TypeScript · Groq · Claude Haiku · OpenAI Embeddings · Supabase pgvector · Vercel

---

## 1. Objectif produit

SAIF-IA est un agent IA de portfolio conçu pour qualifier les recruteurs, présenter le parcours de Saïfallah MANSOUR et orienter vers le bon canal de contact.

Fonctions principales :
- classifier la société du recruteur (client final vs ESN/SSII) automatiquement à l'arrivée ;
- adapter le pitch selon le secteur (banque, HealthTech, startup IA, industrie…) ;
- rechercher dans le CV et le knowledge serveur pour des réponses précises ;
- analyser les repos GitHub à la demande (langages, vélocité, activité) ;
- filtrer les ESN/SSII et réserver le contact aux clients finaux uniquement.

---

## 2. Architecture globale

![Architecture globale](../../docs/diagrams/01-architecture-globale.svg)

---

## 3. Diagramme de séquence — Flux principal (question avec tools)

![Flux principal](../../docs/diagrams/02-flux-principal.svg)

---

## 4. Diagramme de séquence — analyze_github_repo

![analyze_github_repo](../../docs/diagrams/03-analyze-github-repo.svg)

---

## 5. Diagramme de séquence — web_research_recruiter (3 tiers)

![web_research_recruiter](../../docs/diagrams/04-web-research-recruiter.svg)

---

## 6. Diagramme de séquence — Qualification contact (téléphone)

![Qualification contact](../../docs/diagrams/05-qualification-contact.svg)

---

## 7. Routing multi-LLM — flowchart décisionnel

![Routing multi-LLM](../../docs/diagrams/06-routing-multi-llm.svg)

---

## 8. Catalogue des 5 MCP Tools

| Tool | Trigger | Sources | Latence typ. |
|------|---------|---------|-------------|
| `search_cv(query)` | Compétences, missions, stack, projets | `data.ts` + `chatbot-knowledge.ts` (serveur) | < 5ms |
| `get_github_repos()` | "code", "repo", "GitHub", "portfolio" | GitHub API `/users/Sayfouche/repos` | ~200ms |
| `analyze_github_repo(repo_name)` | "analyse repo", "détail projet", "commits" | GitHub API (3 endpoints parallèles) | ~400ms |
| `web_research_recruiter(company)` | Toute session avec `recruiter.company` (1er msg) | Statique (Tier 1/2) ou Claude sub-call (Tier 3) | < 1ms / ~800ms |
| `schedule_meeting()` | Après qualification client final complète | `NEXT_PUBLIC_CALENDLY_URL` (env var) | < 1ms |

### Implémentation : analyze_github_repo

```typescript
// 3 appels GitHub en séquence
GET /repos/Sayfouche/{repo}           → metadata (stars, issues, pushed_at)
GET /repos/Sayfouche/{repo}/languages → breakdown % (top 3)
GET /repos/Sayfouche/{repo}/commits?since=30j → vélocité (count)

// Gestion d'erreurs
404 → "Repo introuvable"
409 → repo vide, commitCount = "0"
GITHUB_TOKEN → optionnel, passe de 60 à 5000 req/h
```

### Implémentation : web_research_recruiter (3 tiers)

```typescript
// Tier 1 — statique SSII (34 entrées, 0 API)
KNOWN_SSII: ["capgemini", "accenture", "sopra steria", "atos", "cgi", ...]

// Tier 2 — statique client final (16 entrées, 0 API)
KNOWN_CLIENT_FINAL: { "bnp paribas": {sector, profile}, "société générale": {...}, ... }

// Tier 3 — Claude sub-call (sociétés inconnues)
claude.messages.create({ model: "claude-haiku-4-5-20251001", max_tokens: 300 })
→ JSON strict : { type, sector, profile, recommendation }
→ strip markdown fences avant JSON.parse()
```

---

## 9. RAG pgvector — Phase 2

### Architecture

```
chatbot-knowledge.ts + data.ts  ──►  run.mjs (ingestion)
                                         │
                                    OpenAI text-embedding-3-small
                                    (1536 dims, $0.02/1M tokens)
                                         │
                                    Supabase knowledge_chunks
                                    (pgvector HNSW index)
                                         │
                                    search_knowledge(query)
                                    ──► embedding query ──► RPC match_knowledge_chunks()
                                    ──► top 5 chunks (similarity > 0.5)
                                    ──► fallback search_cv si vide
```

### Schéma Supabase

```sql
CREATE TABLE knowledge_chunks (
  id        uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  content   text    NOT NULL,
  embedding vector(1536),
  metadata  jsonb   DEFAULT '{}',          -- {category, source}
  created_at timestamptz DEFAULT now()
);
CREATE INDEX ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

CREATE FUNCTION match_knowledge_chunks(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.5,
  match_count     int   DEFAULT 5
) RETURNS TABLE (id uuid, content text, metadata jsonb, similarity float) ...
```

### Chunks ingérés (19 chunks, run.mjs)

| Catégorie | Description |
|-----------|-------------|
| `positioning` | Positionnement cible, valeurs, freelance client final |
| `work_style` | Style de travail, autonomie, delivery-oriented |
| `ideal_mission` | Mission idéale, secteurs, localisation, TJM |
| `certifications` | Certifications Anthropic, Microsoft, NVIDIA, AWS |
| `project_positioning` | SAIF-IA, Resell Radar, CV Critic Agent |
| `faq_contact` | Disponibilité, remote, TJM, ESN response |
| `mission_bnppam_cloud` | BNP AM cloud migration + stack |
| `mission_bnppam_sense` | Sense lead technique + règle RAG |
| `mission_bnppam_jasmine` | Jasmine Data Service Python |
| `mission_sgcib` | SG CIB X-One Clean Architecture |
| `mission_bnppam_2016` | BNP AM rôle hybride BA/Dev |
| `mission_sgss` | SGSS Fund Admin + Glass Custody |
| `profile_summary` | Résumé profil global |
| `skills_backend` / `skills_cloud` / `skills_ai` / `skills_frontend` | Compétences par domaine |
| `project_saif_ia` / `project_resell_radar` | Description technique projets |
| `formation` | Diplôme + langues + formation continue |

### Commande d'ingestion

```bash
npm run ingest-rag
# = node --env-file=.env.local agents/rag-ingest/run.mjs
# Requiert : OPENAI_API_KEY + SUPABASE_URL + SUPABASE_SECRET_KEY
```

---

## 10. Parallel Tool Execution — Phase 4

![Parallel tools](../../docs/diagrams/08-parallel-tools.svg)

### Exemple concret

Un recruteur de Doctolib demande : *"Montre-moi ses projets GitHub et dis-moi si notre profil colle"*

**Avant (séquentiel) :**
```
web_research_recruiter("Doctolib")  → ~800ms
        ↓ attend...
get_github_repos()                  → ~200ms
        ↓
Réponse                    Total : ~1000ms
```

**Après (parallèle) :**
```
web_research_recruiter("Doctolib") ─┐
                                    ├─ Promise.all → ~800ms
get_github_repos()              ────┘
        ↓
Réponse                    Total : ~800ms  (-20%)
```

### Implémentation (route.ts)

```typescript
// Phase 4 — badges émis ensemble, puis exécution parallèle
for (const block of toolBlocks) {
  toolsUsed.push(block.name);
  yield { type: "tool_use", tool: block.name };   // tous les badges d'abord
}
const results = await Promise.all(
  toolBlocks.map(async (block) => ({
    type: "tool_result" as const,
    tool_use_id: block.id,
    content: await executeTool(block.name, block.input),
  }))
);
```

**Contrainte yield/async :** on ne peut pas `yield` à l'intérieur d'un callback `Promise.all` (générateur async). Solution : émettre tous les badges `tool_use` dans une boucle `for` synchrone avant le `Promise.all`.

### System prompt — instruction parallèle

```
OPTIMISATION — APPELS PARALLÈLES :
Quand une question nécessite plusieurs outils indépendants, appelle-les dans
la même réponse — ils s'exécuteront en parallèle côté serveur.
Exemple : "repos + profil société" → get_github_repos() ET web_research_recruiter() ensemble.
```

---

## 11. Streaming SSE — Phase 3

![Streaming SSE](../../docs/diagrams/07-streaming-sse.svg)

### Architecture SSE (route.ts)

```typescript
// Type union des events émis
type SSEEvent =
  | { type: "delta"; text: string }
  | { type: "tool_use"; tool: string }
  | { type: "done"; toolsUsed: string[]; modelUsed: "groq"|"claude"; switchReason: "tools"|"fallback"|null }
  | { type: "error"; message: string };

// Groq — stream:true, chunks via delta.content
async function* groqStream(...): AsyncGenerator<SSEEvent>

// Claude — messages.stream(), events content_block_delta + finalMessage()
async function* claudeStream(...): AsyncGenerator<SSEEvent>

// Response SSE
return new Response(ReadableStream, {
  headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" }
});
```

### Lecture du stream (Chatbot.tsx)

```typescript
// Placeholder vide poussé immédiatement → curseur ▋ animé
setMessages([...userMessages, { role: "assistant", content: "", toolsUsed: [] }]);

// Lecture ligne par ligne
const reader = res.body.getReader();
const decoder = new TextDecoder();
// buffer accumule les chunks incomplets, split sur "\n"
// updateLast() — functional updater sans race condition

// delta  → content += text  (streaming token par token)
// tool_use → toolsUsed.push(tool)  (badge apparaît immédiatement)
// done   → modelUsed + switchReason finalisés
// error  → message d'erreur dans le bubble
```

---

## 10. Séparation contenu public / privé

```
src/lib/data.ts                 → PUBLIC — CV, expériences, projets, skills
src/lib/chatbot-knowledge.ts    → SERVEUR UNIQUEMENT — missions détaillées, contact, TJM, positioning
src/lib/system-prompt.ts        → SERVEUR UNIQUEMENT — qualification, garde-fous, règles CAS A/B/C/D
src/lib/tools.ts                → SERVEUR UNIQUEMENT — executors, KNOWN_SSII/CLIENT_FINAL
```

**Règle de vérité Sense/RAG :**  
Saïfallah a travaillé avec Sense, application qui contient un service AI/RAG documentaire. SAIF-IA ne dit jamais qu'il a *implémenté* ce service — uniquement qu'il y a *travaillé avec* en tant que lead technique.

---

## 11. Journalisation Supabase

```sql
-- chat_sessions : une ligne par session recruteur
CREATE TABLE chat_sessions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id text NOT NULL UNIQUE,
  firstname text, lastname text, company text, lang text,
  created_at timestamptz DEFAULT now()
);

-- chat_messages : tous les échanges + outils utilisés
CREATE TABLE chat_messages (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id text NOT NULL,
  role text NOT NULL,       -- "user" | "assistant"
  content text NOT NULL,
  tools_used text[],        -- ["search_cv", "analyze_github_repo", ...]
  created_at timestamptz DEFAULT now()
);
```

Supabase est **optionnel** : le chatbot fonctionne sans logger (fire-and-forget, jamais bloquant).

---

## 12. Variables d'environnement

| Variable | Scope | Obligatoire | Description |
|----------|-------|-------------|-------------|
| `ANTHROPIC_API_KEY` | Serveur | Oui | Claude Haiku tool use + sub-calls |
| `GROQ_API_KEY` | Serveur | Oui | Groq llama-3.3-70b (fast path) |
| `NEXT_PUBLIC_CALENDLY_URL` | Client + Serveur | Oui | Lien booking recruteur |
| `CONTACT_PHONE` | Serveur | Oui | Téléphone privé (révélé après qualification) |
| `SUPABASE_URL` | Serveur | Non | Logging sessions |
| `SUPABASE_SECRET_KEY` | Serveur | Non | Logging sessions |
| `GITHUB_TOKEN` | Serveur | Non | 5000 req/h au lieu de 60 (analyze_github_repo) |
| `LLM_PROVIDER` | Serveur | Non | `"claude"` pour forcer Claude en dev |

---

## 13. Roadmap technique

| Phase | Fonctionnalité | Statut |
|-------|---------------|--------|
| Phase 1 | 5 MCP tools (search_cv, get_github_repos, schedule_meeting, analyze_github_repo, web_research_recruiter) | ✅ **Livré** |
| Phase 2 | RAG pgvector — Supabase pgvector (HNSW) + OpenAI text-embedding-3-small + tool search_knowledge | ✅ **Livré** |
| Phase 3 | Streaming SSE — affichage token par token (Next.js App Router + Anthropic stream) | ✅ **Livré** |
| Phase 4 | Parallel tool execution — Promise.all sur multi-tool blocks + system prompt parallèle | ✅ **Livré** |
| Phase 5 | CV/LinkedIn update + certif Claude Certified Architect (CCA-F) | 📋 Continu |

---

## 14. Valeur technique démontrée

**Ce que SAIF-IA prouve concrètement :**

- **Claude Tool Use API** — agentic loop 5 itérations, 5 tools définis
- **Multi-model routing** — Groq (vitesse) + Claude Haiku (intelligence), fallback automatique
- **MCP-style tools** — schémas JSON typés, executors TypeScript, routing par switch
- **External API integration** — GitHub REST API (3 endpoints agrégés)
- **LLM sub-call pattern** — Claude appelant Claude pour une classification JSON structurée
- **Smart pre-processing** — tool exécuté server-side avant de passer à Claude (injection contexte)
- **Qualification business logic** — CAS A/B/C/D encodés en system prompt + tool results
- **RAG pgvector** — Supabase pgvector + HNSW index + OpenAI text-embedding-3-small + cosine similarity + fallback gracieux
- **Parallel tool execution** — `Promise.all` sur multi-tool blocks, -20% latence sur appels multi-outils
- **Streaming SSE** — `ReadableStream` + async generators, token par token, tool badges en temps réel
- **Privacy by design** — knowledge serveur jamais sérialisé côté client

> *"Vous êtes en train d'utiliser ce qu'il a construit — et je viens d'appeler un outil là 😄"*
