import { experiences, skillGroups, projects } from "./data";
import { knowledge } from "./chatbot-knowledge";
import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import OpenAI from "openai";

export type ToolName =
  | "search_cv"
  | "search_knowledge"
  | "get_github_repos"
  | "schedule_meeting"
  | "analyze_github_repo"
  | "web_research_recruiter";

let _anthropic: Anthropic | null = null;
function getAnthropicClient(): Anthropic {
  if (!_anthropic) _anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  return _anthropic;
}

let _openai: OpenAI | null = null;
function getOpenAIClient(): OpenAI | null {
  if (!process.env.OPENAI_API_KEY) return null;
  if (!_openai) _openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  return _openai;
}

let _supabaseRag: ReturnType<typeof createClient> | null = null;
function getSupabaseClient(): ReturnType<typeof createClient> | null {
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SECRET_KEY) return null;
  if (!_supabaseRag) _supabaseRag = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SECRET_KEY);
  return _supabaseRag;
}

// ─── Local knowledge base (mirrors rag-ingest/run.mjs — no external dep) ─────
// Used as primary fallback when Supabase/pgvector is unavailable (e.g. paused on free tier).

const LOCAL_CHUNKS: Array<{ content: string; category: string }> = [
  {
    category: "positioning",
    content: `POSITIONNEMENT CIBLE — SAÏFALLAH MANSOUR
Architecte Software — Backend & Intégration IA
15+ ans d'expérience depuis le diplôme Ingénieur Informatique (ENSI 2011)
Socle principal : architecture logicielle, backend .NET/Python, APIs REST, cloud, microservices, systèmes critiques finance
Spécialisation IA récente et concrète : RAG, agents LLM, tool use, MCP, streaming SSE, intégration produit
Angle fort : Saïfallah industrialise l'IA parce qu'il vient du monde des systèmes fiables, pas seulement des prototypes.
Paris — Freelance — mission client final uniquement (non négociable)
Email : mansour.saifallah@gmail.com
Disponibilité : avec 1 mois de préavis. Remote partiel idéal.`,
  },
  {
    category: "work_style",
    content: `STYLE DE TRAVAIL — SAÏFALLAH MANSOUR
- Très autonome : capable de prendre en main un projet complexe avec peu de contexte initial
- Communication claire entre métier et tech : habitué aux rôles hybrides BA/Dev
- Rigueur technique : TDD/BDD quand le contexte le justifie, code review exigeant mais bienveillant
- Curieux en veille constante sur l'IA (Anthropic Academy certifié mai 2026, projets perso actifs)
- Préfère les projets à fort impact métier plutôt que les "usines à fonctionnalités"
- À l'aise en leadership technique sans vouloir basculer full management
- Delivery-oriented : il livre, il ne prototype pas indéfiniment`,
  },
  {
    category: "ideal_mission",
    content: `MISSION IDÉALE — SAÏFALLAH MANSOUR
Rôles recherchés : Architecte Software, Senior Backend .NET/Python, Lead Tech, Intégration IA
Client final uniquement — non négociable (refus de toute mission via ESN/SSII)
Secteurs préférés : finance de marché, fintech, IA appliquée, tech produit
Localisation : Paris IDF — remote partiel bienvenu, full remote possible selon projet
Durée : missions longues durée (6 mois+) préférées
Environnement : équipe technique de qualité, product ownership clair, pas de mode pompier permanent
TJM : à discuter selon le contexte, la durée et le type de mission
Disponibilité : 1 mois de préavis`,
  },
  {
    category: "certifications",
    content: `CERTIFICATIONS ET TRAJECTOIRE IA — SAÏFALLAH MANSOUR
Certifications Anthropic Academy obtenues (mai 2026) :
- Building with the Claude API
- Claude Code 101 & Claude Code in Action
- Introduction to agent skills
- Introduction to Model Context Protocol
- Model Context Protocol Advanced Topics
- AI Fluency Framework & Foundations
- AI Fluency for Small Businesses

Certifications en cours / objectif court terme :
- Microsoft AI Solution Lead (vision executive/business et architecture solutions IA)
- NVIDIA Generative AI / LLM (GenAI engineering et compréhension des modèles)

Planifiée : AWS AI Practitioner (cloud IA multi-provider)

Lecture tactique : La preuve principale reste 15+ ans d'architecture logicielle, le delivery cloud/microservices en SI critique, et les projets IA concrets. Les certifications renforcent la cohérence de la trajectoire.`,
  },
  {
    category: "project_positioning",
    content: `POSITIONNEMENT DES PROJETS IA — SAÏFALLAH MANSOUR
SAIF-IA Chatbot : agent IA de portfolio. Objectif : qualifier recruteurs, présenter le parcours, adapter le pitch, orienter vers le contact. 6 tools, Claude Tool Use API, multi-LLM routing (Groq + Claude Haiku), streaming SSE, RAG pgvector.
CV Critic Agent : agent interne distinct, extrait dans un repo autonome. Objectif opposé : critiquer le CV, détecter les faiblesses, challenger la crédibilité IA, générer des rapports versionnés. Migration technique documentée : Node.js legacy → script CrewAI Python → CrewAI native, avec tests mock et provider Mistral par défaut.
Resell Radar : veille automatisée d'annonces publiques et scoring IA. Python, Playwright, Mistral LLM, Telegram alerts. Collecte contrôlée, respect des limites, aide à la décision.
SAIF-IA est la démonstration publique : vous l'utilisez en ce moment même.`,
  },
  {
    category: "faq_contact",
    content: `FAQ — SAÏFALLAH MANSOUR
Disponibilité : disponible avec 1 mois de préavis.
Remote : remote partiel idéal. Full remote possible selon le projet.
TJM : à discuter selon le contexte, la durée et le type de mission.
Relocalisation : basé à Paris, pas de relocalisation.
Secteurs cibles : finance de marché, fintech, IA appliquée, tech produit.
Type de contrat : freelance client final uniquement.
ESN/SSII : non, ce n'est pas négociable. Saïfallah travaille exclusivement en client final.
Contact téléphonique : communiqué directement après qualification (nom, prénom, société client final confirmée).
Rendez-vous : via lien Calendly (communiqué après qualification).`,
  },
  {
    category: "mission_bnppam_cloud",
    content: `MISSION BNP PARIBAS ASSET MANAGEMENT — Août 2022 → Présent (CLOUD & ARCHITECTURE)
Contexte : programme de transformation du SI, modernisation applicative, migration progressive vers IBM Cloud dans un SI bancaire exigeant (Asset Management).
Rôle : intervention initiale en Senior Software Engineer, évolution vers Technical Lead avec responsabilités d'architecture applicative.
Stack : .NET 6/8, ASP.NET Core, Python FastAPI, Kafka, PostgreSQL, IBM Cloud, IKS, Kubernetes, Docker, Helm, Azure DevOps, CI/CD YAML, Vault, SonarQube.
Activités cloud : études de migrabilité, analyse dépendances, architectures cibles cloud-native IBM Cloud, modernisation legacy vers microservices, migration SQL Server vers PostgreSQL Cloud, études Oracle → PostgreSQL.`,
  },
  {
    category: "mission_bnppam_sense",
    content: `MISSION BNP PARIBAS ASSET MANAGEMENT — Leadership Technique — Application Sense
Sense : plateforme Multi Asset pour analystes internes (7 microservices + frontend React, ~120 utilisateurs internes).
Rôle : lead technique officiel, coordination jusqu'à ~10 personnes, puis noyau réduit ~3 personnes.
Fonctions Sense : consultation données financières, analyse d'instruments, ratings/research, aide à la décision d'investissement, partage d'analyses métier.
Service AI/RAG : Sense contient un service documentaire IA de type RAG (équipe dédiée). Saïfallah a participé à l'étude et au suivi technique (définition API, points de contact) — il ne l'a pas implémenté. Formulation autorisée : "exposition professionnelle concrète à un cas d'usage IA/RAG en Asset Management".
Responsabilités : coordination technique, résolution de blocages, code reviews backend, cadrage technique des besoins métier, suivi des dépendances inter-équipes.`,
  },
  {
    category: "mission_bnppam_jasmine",
    content: `MISSION BNP PARIBAS ASSET MANAGEMENT — Projet Stratégique Jasmine
Jasmine : plateforme stratégique d'intégration de portefeuilles externes. Architecture microservices (REST + Kafka), backends Python FastAPI et .NET, frontend React/TypeScript, Kubernetes IBM Cloud.
Contribution principale : Data Service Python FastAPI — récupération de données financières et conformité, agrégation multi-systèmes, préparation pour services de calcul, orchestration de traitements techniques, mapping et normalisation de données métier.
Responsabilités : gestion des flux Kafka, cache multi-niveaux (mémoire + IBM COS), optimisation backend, batchs et traitements asynchrones, participation à l'architecture microservices, interventions ponctuelles .NET.`,
  },
  {
    category: "mission_sgcib",
    content: `MISSION SOCIÉTÉ GÉNÉRALE CIB — Décembre 2018 → Août 2022 — X-One (Back Office Equity)
Projet X-One : un des plus grands projets trading de SG CIB, ~200 développeurs.
Rôle : Senior Software Engineer, pilote technique, release manager.
Réalisations clés : réduction du temps de traitement batch de ~40%, implémentation Clean Architecture sur nouveaux modules, migration mocks Rhino → Moq, migration csproj SDK Style, implémentation TDD/BDD, SonarQube.
Release manager : coordination entre 5+ équipes feature, planification des releases.
Mentor : junior developers, pair programming régulier, code reviews.
Stack : C# .NET 4.6/4.8/Core 2.2, ASP.NET Core WebAPI, Jenkins, Oracle, Sybase, PostgreSQL, NUnit, SpecFlow, Autofac.`,
  },
  {
    category: "mission_bnppam_2016",
    content: `MISSION BNP PARIBAS ASSET MANAGEMENT — Septembre 2016 → Décembre 2018
Rôle hybride : Business Analyst et développeur .NET, interface directe avec le métier (Front Office, Middle Office).
Application owner sur 2 applications critiques de reporting réglementaire.
Activités : rédaction specs fonctionnelles détaillées (UML/BPMN), coordination MOE/MOA, développement full-stack, création de POCs, gestion exigences, responsabilité technique des décisions projet.
Stack : .NET, TDD, NUnit, Oracle SQL Developer, C#, HTML.`,
  },
  {
    category: "mission_sgss",
    content: `MISSION SOCIÉTÉ GÉNÉRALE SECURITIES SERVICES (SGSS) — Février 2013 → Août 2016
Équipe Gallery (Fund Admin) : application de reporting NAV/GED pour 100+ fonds d'investissement. Maintenance corrective et évolutive. Développement web services inter-applicatifs (WCF, ASMX). Intégration ETL multi-pays. REST client OAuth 2.0. Stack : C#, ASP.NET, WCF, Oracle, PLSQL, ETL, Bootstrap, jQuery.
Équipe Glass Custody : maintenance GCU et Glass Admin. Réplication données Oracle Jobs, import/export, custodisation. Stack : C#, Oracle, PLSQL.
Première expérience en finance de marché, culture craftsmanship.`,
  },
  {
    category: "profile_summary",
    content: `PROFIL — SAÏFALLAH MANSOUR
Architecte solution software et ingénieur IA appliquée avec 15+ ans d'expérience en finance de marché, backend .NET/Python et systèmes critiques.
Spécialisé dans la conception d'APIs REST, l'architecture Clean/DDD, la migration Cloud et l'industrialisation de plateformes fiables.
Spécialisation IA appliquée : RAG, agents LLM, tool use, MCP, streaming SSE — certifié Anthropic Academy (mai 2026).
Projets personnels livrés : SAIF-IA Chatbot (portfolio agent IA), Resell Radar (veille automatisée), CV Critic Agent (agent critique interne).
Parcours : ENSI Ingénieur Informatique (2011) → 4 ans SGSS → 2 ans BNP AM → 4 ans SG CIB → 3 ans BNP AM (actuel).`,
  },
  {
    category: "skills_backend",
    content: `COMPÉTENCES BACKEND & ARCHITECTURE — SAÏFALLAH MANSOUR
C# / .NET (expert, 15+ ans) : ASP.NET Core, WebAPI, Entity Framework Core, WCF, NUnit, SpecFlow, Autofac, Moq
Python (avancé) : FastAPI, AsyncIO, HTTPX, Pytest, Pytest-AsyncIO, pandas
Architecture : Clean Architecture, DDD, SOA, Microservices, Design Patterns, Event-driven (Kafka)
APIs : REST, GraphQL, WebSockets, SignalR
Sécurité : OAuth 2.0, SAML 2.0, SSO, JWT
Base de données : PostgreSQL, Oracle, SQL Server, Sybase, PLSQL, ETL`,
  },
  {
    category: "skills_cloud",
    content: `COMPÉTENCES CLOUD & DEVOPS — SAÏFALLAH MANSOUR
Cloud : IBM Cloud (IKS, COS, Event Streams), Azure DevOps, AWS (notions)
Conteneurs : Docker, Kubernetes, Helm
CI/CD : Azure DevOps pipelines YAML, Jenkins, SonarQube, Fortify, Vault
Monitoring : Kibana, DataDog (notions)
Méthodes : Scrum, Kanban, SAFe, TDD, BDD, Code Review, UML, BPMN`,
  },
  {
    category: "skills_ai",
    content: `COMPÉTENCES IA & LLM — SAÏFALLAH MANSOUR
LLM APIs : Claude (Anthropic) — Tool Use, Streaming SSE, Structured Outputs, MCP, agentic loops
Groq API : llama-3.3-70b, fast inference, streaming
RAG (Retrieval-Augmented Generation) : pgvector, HNSW index, semantic search, embeddings
Frameworks : agents LLM, multi-model routing, parallel tool execution
Embeddings : OpenAI text-embedding-3-small, Supabase pgvector
Outils IA : Claude Code CLI, Anthropic Academy certifié, MCP tools design
Projets IA livrés : SAIF-IA Chatbot (6 tools, streaming, RAG), Resell Radar (scraping + Mistral scoring), CV Critic Agent`,
  },
  {
    category: "skills_frontend",
    content: `COMPÉTENCES FRONTEND — SAÏFALLAH MANSOUR
TypeScript (avancé), React, Next.js 16 App Router, JavaScript ES6+
CSS : Tailwind CSS, Bootstrap, Framer Motion
Outils : Webpack, ESLint, Prettier
HTML/CSS, jQuery (legacy)
Backend-for-frontend : SSR Next.js, Server Components, Route Handlers`,
  },
  {
    category: "project_saif_ia",
    content: `PROJET SAIF-IA CHATBOT (portfolio personnel)
Agent IA de portfolio conçu pour qualifier les recruteurs et présenter le parcours de Saïfallah.
Stack : Next.js 16, TypeScript, Claude Haiku (Anthropic Tool Use API), Groq (llama-3.3-70b), Supabase (PostgreSQL + pgvector), Vercel.
6 Tools : search_cv, search_knowledge (RAG), get_github_repos, analyze_github_repo, web_research_recruiter, schedule_meeting.
Fonctionnalités : multi-LLM routing (Groq pour vitesse, Claude pour tool use), streaming SSE token par token, agentic loop 5 itérations, classification ESN/client final 3 tiers, qualification recruteur CAS A/B/C/D, RAG pgvector.
Déployé sur Vercel. Code source privé (Sayfouche/cv-portfolio).
Ce que ça prouve : Claude Tool Use API, MCP-style tools, streaming SSE, RAG pgvector, multi-model routing, privacy by design.`,
  },
  {
    category: "project_resell_radar",
    content: `PROJET RESELL RADAR (projet personnel)
Système de veille automatisée d'annonces publiques avec scoring IA.
Stack : Python, Playwright (scraping), Mistral LLM (scoring et analyse), Telegram (alerting), PostgreSQL.
Fonctionnalités : collecte contrôlée d'annonces publiques, scoring métier via LLM, alertes Telegram en temps réel, tableau de bord d'analyse.
Usage : aide à la décision sur des opportunités de revente, détection d'anomalies de prix.
Approche : collecte respectueuse des limites, pas de scraping agressif, usages raisonnables.`,
  },
  {
    category: "formation",
    content: `FORMATION — SAÏFALLAH MANSOUR
Diplôme : Ingénieur en Informatique — ENSI (École Nationale des Sciences de l'Informatique), 2011
Langues : Français (courant), Anglais (courant)
Formation continue IA : Anthropic Academy (8 certifications obtenues en mai 2026)
En cours : Microsoft AI Solution Lead, NVIDIA Generative AI/LLM
Planifié : AWS AI Practitioner`,
  },
];

// Normalize text for scoring: remove accents, lowercase, tokenize
function normalizeForSearch(text: string): string[] {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .split(/[\s,;:.?!()\[\]{}"'\/\\-]+/)
    .filter((w) => w.length > 2);
}

// Score-based local search over all knowledge chunks (no external dep)
function searchLocal(query: string): string {
  const queryWords = normalizeForSearch(query);
  if (!queryWords.length) return `Aucun résultat pour "${query}".`;

  const scored = LOCAL_CHUNKS.map((chunk) => {
    const chunkWords = normalizeForSearch(chunk.content);
    let score = 0;
    for (const qw of queryWords) {
      for (const cw of chunkWords) {
        if (cw === qw) score += 2;
        else if (cw.startsWith(qw) || qw.startsWith(cw)) score += 1;
      }
    }
    return { ...chunk, score };
  })
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);

  if (!scored.length) return `Aucun résultat pour "${query}" dans la base de connaissances.`;
  return scored.map((c) => `[${c.category}]\n${c.content}`).join("\n\n---\n\n");
}

// ─── Executors ────────────────────────────────────────────────────────────────

function searchCv(query: string): string {
  const q = query.toLowerCase();
  const hits: string[] = [];

  experiences.forEach((e) => {
    const inStack = e.stack.some((s) => s.toLowerCase().includes(q));
    const allBullets = [...e.bulletsFr, ...(e.subSections?.flatMap((s) => s.bulletsFr) ?? [])];
    const inBullets = allBullets.some((b) => b.toLowerCase().includes(q));
    if (e.company.toLowerCase().includes(q) || e.roleFr.toLowerCase().includes(q) || inStack || inBullets) {
      hits.push(
        `[Expérience] ${e.company} (${e.period}) — ${e.roleFr}\nStack: ${e.stack.join(", ")}\n${allBullets.join("\n")}`
      );
    }
  });

  skillGroups.forEach((g) => {
    const matched = g.skills.filter((s) => s.name.toLowerCase().includes(q));
    if (matched.length || g.categoryFr.toLowerCase().includes(q)) {
      hits.push(`[Compétences — ${g.categoryFr}] ${(matched.length ? matched : g.skills).map((s) => s.name).join(", ")}`);
    }
  });

  projects.forEach((p) => {
    if (p.name.toLowerCase().includes(q) || p.descFr.toLowerCase().includes(q) || p.stack.some((s) => s.toLowerCase().includes(q))) {
      hits.push(`[Projet] ${p.name}: ${p.descFr} (${p.stack.join(", ")})`);
    }
  });

  Object.values(knowledge.missions).forEach((val) => {
    if (val.toLowerCase().includes(q)) {
      hits.push(`[Détail mission] ${val}`);
    }
  });

  [knowledge.positioning, knowledge.certificationPlan, knowledge.projectPositioning, knowledge.workStyle, knowledge.idealMission].forEach((val) => {
    if (val.toLowerCase().includes(q)) {
      hits.push(`[Knowledge SAIF-IA] ${val}`);
    }
  });

  if (!hits.length) return `Aucun résultat pour "${query}" dans le CV.`;
  return hits.slice(0, 5).join("\n\n");
}

async function searchKnowledge(query: string): Promise<string> {
  const openai = getOpenAIClient();
  const supabase = getSupabaseClient();

  // No external clients → use rich local search (fast, no network dependency)
  if (!openai || !supabase) return searchLocal(query);

  try {
    const embRes = await openai.embeddings.create({
      model: "text-embedding-3-small",
      input: query,
    });
    const embedding = embRes.data[0].embedding;

    // Supabase rpc() requires Database schema generics for typed args — cast to bypass
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data, error } = await (supabase as any).rpc("match_knowledge_chunks", {
      query_embedding: embedding,
      match_threshold: 0.3,  // lowered from 0.5 — catches more semantic matches
      match_count: 5,
    });

    // Supabase unavailable (paused free tier) or no matches → fall back to local search
    if (error || !data?.length) return searchLocal(query);

    // Deduplicate by category (pgvector can return dupes after multiple ingests)
    const seen = new Set<string>();
    const unique = (data as Array<{ content: string; metadata: { category?: string }; similarity: number }>)
      .filter((c) => {
        const key = c.metadata?.category ?? c.content.slice(0, 40);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });

    return unique
      .map((c) => `[${c.metadata?.category ?? "knowledge"} · ${(c.similarity * 100).toFixed(0)}%]\n${c.content}`)
      .join("\n\n");
  } catch {
    // Network failure (e.g. Supabase project paused) → degrade gracefully
    return searchLocal(query);
  }
}

async function fetchGithubRepos(): Promise<string> {
  try {
    const res = await fetch("https://api.github.com/users/Sayfouche/repos?sort=updated&per_page=8", {
      headers: { Accept: "application/vnd.github.v3+json" },
      next: { revalidate: 3600 },
    });
    if (!res.ok) return "GitHub API indisponible pour le moment.";
    const repos: { name: string; language: string | null; description: string | null; stargazers_count: number; fork: boolean; html_url: string }[] = await res.json();
    const filtered = repos.filter((r) => !r.fork).slice(0, 5);
    if (!filtered.length) return "Aucun repo public trouvé.";
    return filtered
      .map((r) => `• ${r.name} (${r.language ?? "—"}) — ${r.description ?? "pas de description"} ⭐${r.stargazers_count} → ${r.html_url}`)
      .join("\n");
  } catch {
    return "Impossible de récupérer les repos GitHub.";
  }
}

async function analyzeGithubRepo(repoName: string): Promise<string> {
  if (!repoName) return "Nom du repo manquant.";
  const base = `https://api.github.com/repos/Sayfouche/${encodeURIComponent(repoName)}`;
  const headers: Record<string, string> = { Accept: "application/vnd.github.v3+json" };
  if (process.env.GITHUB_TOKEN) headers["Authorization"] = `Bearer ${process.env.GITHUB_TOKEN}`;

  try {
    const repoRes = await fetch(base, { headers });
    if (repoRes.status === 404) return `Repo "${repoName}" introuvable sur le compte GitHub de Saïfallah.`;
    if (!repoRes.ok) return `GitHub API indisponible (${repoRes.status}).`;

    const repo = await repoRes.json() as {
      name: string; description: string | null; stargazers_count: number;
      open_issues_count: number; pushed_at: string; language: string | null; html_url: string;
    };

    const langRes = await fetch(`${base}/languages`, { headers });
    let languageStr = repo.language ?? "—";
    if (langRes.ok) {
      const langs = await langRes.json() as Record<string, number>;
      const total = Object.values(langs).reduce((a, b) => a + b, 0);
      if (total > 0) {
        languageStr = Object.entries(langs)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 3)
          .map(([name, bytes]) => `${name} ${Math.round((bytes / total) * 100)}%`)
          .join(", ");
      }
    }

    const since = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
    const commitsRes = await fetch(`${base}/commits?since=${since}&per_page=100`, { headers });
    let commitCount = "N/A";
    if (commitsRes.ok) {
      const commits = await commitsRes.json() as unknown[];
      commitCount = String(commits.length);
    } else if (commitsRes.status === 409) {
      commitCount = "0";
    }

    const lastPush = repo.pushed_at
      ? new Date(repo.pushed_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" })
      : "—";

    return (
      `**${repo.name}** — ${repo.description ?? "pas de description"}\n` +
      `• Langages : ${languageStr}\n` +
      `• Commits (30 derniers jours) : ${commitCount}\n` +
      `• Issues ouvertes : ${repo.open_issues_count}\n` +
      `• Étoiles : ${repo.stargazers_count}\n` +
      `• Dernière activité : ${lastPush}\n` +
      `• URL : ${repo.html_url}`
    );
  } catch {
    return `Impossible d'analyser le repo "${repoName}" — GitHub API inaccessible.`;
  }
}

// ─── Static knowledge for web_research_recruiter ─────────────────────────────

const KNOWN_SSII = [
  "capgemini", "sopra steria", "soprasteria", "accenture", "atos", "cgi",
  "alten", "altran", "sqli", "devoteam", "aubay", "sogeti", "wavestone",
  "onepoint", "inetum", "sii", "scalian", "apside", "amiltone", "infotel",
  "neurones", "orange consulting", "dxc", "ibm consulting", "kyndryl",
  "tata consultancy", "tcs", "infosys", "wipro", "hcl technologies",
  "cognizant", "ntt data", "publicis sapient",
];

const KNOWN_CLIENT_FINAL: Record<string, { sector: string; profile: string }> = {
  "bnp paribas": { sector: "Banque / Asset Management", profile: "Grand compte, transformation cloud & IA, SI critique finance de marché" },
  "bnp paribas asset management": { sector: "Asset Management", profile: "Migration cloud IBM, microservices, Python/.NET, équipes 10+ devs" },
  "société générale": { sector: "Banque / CIB", profile: "Grand compte, trading platforms, SI critique, microservices" },
  "sgcib": { sector: "Banque / CIB", profile: "Trading platform X-One, forte culture technique" },
  "sgss": { sector: "Securities Services", profile: "Custodisation, reporting NAV, Oracle" },
  "axa": { sector: "Assurance", profile: "Grand compte, transformation digitale, cloud" },
  "natixis": { sector: "Banque / Asset Management", profile: "Grand compte, finance de marché" },
  "airbus": { sector: "Aéronautique / Industrie", profile: "Grand compte, systèmes critiques, embarqué & IT" },
  "totalenergies": { sector: "Énergie", profile: "Grand compte, digitalisation, data" },
  "total": { sector: "Énergie", profile: "Grand compte, digitalisation, data" },
  "renault": { sector: "Automobile / Industrie", profile: "Grand compte, transformation digitale" },
  "lvmh": { sector: "Luxe / Retail", profile: "Grand compte, e-commerce, digital" },
  "sncf": { sector: "Transport / Public", profile: "Grand compte, modernisation SI" },
  "credit agricole": { sector: "Banque", profile: "Grand compte, retail banking, transformation" },
  "crédit agricole": { sector: "Banque", profile: "Grand compte, retail banking, transformation" },
  "la banque postale": { sector: "Banque", profile: "Grand compte, services financiers" },
  "amundi": { sector: "Asset Management", profile: "Grand compte, gestion d'actifs, IA financière" },
};

function matchKnownCompany(company: string): { type: "ssii" } | { type: "client_final"; sector: string; profile: string } | null {
  const key = company.toLowerCase().trim();
  if (KNOWN_SSII.some((s) => key.includes(s))) return { type: "ssii" };
  for (const [name, info] of Object.entries(KNOWN_CLIENT_FINAL)) {
    if (key.includes(name) || name.includes(key)) return { type: "client_final", ...info };
  }
  return null;
}

async function researchRecruiterCompany(company: string): Promise<string> {
  if (!company) return "Nom de société manquant.";

  const matched = matchKnownCompany(company);

  if (matched?.type === "ssii") {
    return (
      `**${company}** — Classification : ESN / SSII\n` +
      `• Type : Société de services en ingénierie informatique\n` +
      `• Action SAIF-IA : demander le contexte de mission, l'équipe, la durée et le mode de collaboration envisagé.`
    );
  }

  if (matched?.type === "client_final") {
    return (
      `**${company}** — Type : Entreprise utilisatrice\n` +
      `• Secteur : ${matched.sector}\n` +
      `• Profil entreprise : ${matched.profile}\n` +
      `• Recommandation : mettre en avant le socle finance de marché / architecture cloud / backend critique.`
    );
  }

  try {
    const client = getAnthropicClient();
    const res = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 300,
      messages: [{
        role: "user",
        content:
          `Analyse rapide de la société "${company}" pour un recruteur IT en France.\n` +
          `Réponds UNIQUEMENT avec ce JSON strict (sans markdown) :\n` +
          `{"type":"client_final"|"ssii"|"inconnu","sector":"...","profile":"...","recommendation":"..."}\n` +
          `- type: "ssii" si ESN/SSII/cabinet placement, "client_final" si recrutement interne IT, "inconnu" sinon\n` +
          `- sector: secteur d'activité\n` +
          `- profile: 1 phrase sur le profil IT\n` +
          `- recommendation: 1 phrase sur comment présenter Saïfallah (architecte software / backend .NET-Python / IA appliquée)`,
      }],
    });

    const raw = (res.content.find((b) => b.type === "text") as Anthropic.TextBlock | undefined)?.text ?? "";
    const cleaned = raw.replace(/```json\n?|\n?```/g, "").trim();
    const parsed = JSON.parse(cleaned) as { type: string; sector: string; profile: string; recommendation: string };

    const typeLabel = parsed.type === "ssii" ? "ESN / SSII" : parsed.type === "client_final" ? "Entreprise utilisatrice" : "Classification incertaine";
    return (
      `**${company}** — Type : ${typeLabel}\n` +
      `• Secteur : ${parsed.sector}\n` +
      `• Profil : ${parsed.profile}\n` +
      `• Recommandation : ${parsed.recommendation}`
    );
  } catch {
    return (
      `**${company}** — Analyse indisponible.\n` +
      `• Recommandation : demander directement le contexte de mission, l'équipe et le mode de collaboration envisagé.`
    );
  }
}

function getMeetingLink(): string {
  const url = process.env.NEXT_PUBLIC_CALENDLY_URL;
  if (!url || url.includes("REMPLACE"))
    return "Le calendrier n'est pas encore configuré. Contactez Saïfallah directement par email : mansour.saifallah@gmail.com";
  return `Voici le lien pour réserver directement un créneau dans l'agenda de Saïfallah : ${url}\nIl confirme sous 24h.`;
}

// ─── Tool definitions (provider-agnostic) ─────────────────────────────────────

export const toolDefinitions = [
  {
    name: "search_knowledge",
    description:
      "Semantic RAG search in Saïfallah's knowledge base (pgvector). PREFERRED over search_cv for nuanced questions about positioning, work style, ideal mission, certifications, mission details, soft skills, and availability. Falls back to keyword search if RAG not configured.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Natural language query (e.g. 'style de travail', 'disponibilité et TJM', 'mission Sense leadership', 'certifications IA')" },
      },
      required: ["query"],
    },
  },
  {
    name: "search_cv",
    description:
      "Keyword search in Saïfallah's CV. Use for specific technology or company lookups (e.g. 'Python', 'BNP Paribas'). Prefer search_knowledge for open-ended questions.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search query (e.g. 'Python', 'BNP Paribas', 'RAG', 'microservices')" },
      },
      required: ["query"],
    },
  },
  {
    name: "get_github_repos",
    description:
      "Fetch Saïfallah's live public GitHub repositories. Use when a recruiter wants to see real code or concrete projects.",
    parameters: { type: "object", properties: {} },
  },
  {
    name: "schedule_meeting",
    description:
      "Get the Calendly link to book a phone call with Saïfallah. Use ONLY when the recruiter is fully qualified: name and company provided.",
    parameters: { type: "object", properties: {} },
  },
  {
    name: "analyze_github_repo",
    description:
      "Fetch detailed analysis of a specific GitHub repository by Saïfallah: language breakdown (%), commit count over last 30 days, open issues, stars, last push date. Use when a recruiter asks to dive into a specific project or wants technical metrics on a repo.",
    parameters: {
      type: "object",
      properties: {
        repo_name: { type: "string", description: "Exact repository name as it appears on GitHub (e.g. 'cv-portfolio', 'resell-radar')" },
      },
      required: ["repo_name"],
    },
  },
  {
    name: "web_research_recruiter",
    description:
      "Research and classify the recruiter's company, identifies the sector, and generates a pitch recommendation for Saïfallah. Call automatically as soon as the recruiter's company name is known.",
    parameters: {
      type: "object",
      properties: {
        company: { type: "string", description: "Company name as provided by the recruiter (e.g. 'BNP Paribas', 'Capgemini', 'Doctolib')" },
      },
      required: ["company"],
    },
  },
];

export async function executeTool(name: ToolName, args: Record<string, unknown>): Promise<string> {
  switch (name) {
    case "search_knowledge":
      return await searchKnowledge((args.query as string) ?? "");
    case "search_cv":
      return searchCv((args.query as string) ?? "");
    case "get_github_repos":
      return await fetchGithubRepos();
    case "schedule_meeting":
      return getMeetingLink();
    case "analyze_github_repo":
      return await analyzeGithubRepo((args.repo_name as string) ?? "");
    case "web_research_recruiter":
      return await researchRecruiterCompany((args.company as string) ?? "");
    default:
      return "Outil inconnu.";
  }
}
