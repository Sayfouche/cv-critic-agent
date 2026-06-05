export type Lang = "fr" | "en";

// ─── Personal Info ────────────────────────────────────────────────────────────
export const personal = {
  name: "Saïfallah MANSOUR",
  titleFr: "Architecte logiciel — Intégration IA",
  titleEn: "Software Architect — AI Integration",
  subtitle: ".NET · Python · Cloud · Distributed Systems · Applied AI",
  email: "mansour.saifallah@gmail.com",
  phone: "07 81 •• •• 77",
  linkedin: "https://www.linkedin.com/in/saifallah-mansour-18078525/",
  github: "https://github.com/Sayfouche/",
  location: "Paris",
  availabilityFr: "Disponible avec 1 mois de préavis",
  availabilityEn: "Available with 1 month notice",
  statusFr: "Freelance",
  statusEn: "Freelance",
};

// Keep backward-compat alias
export const personalInfo = {
  name: personal.name,
  titleFr: personal.titleFr,
  titleEn: personal.titleEn,
  taglineFr: personal.subtitle,
  taglineEn: personal.subtitle,
  email: personal.email,
  linkedin: personal.linkedin,
  github: personal.github,
  location: personal.location,
};

// ─── Profile summaries ────────────────────────────────────────────────────────
export const profileFr = [
  "Architecte logiciel avec 15+ ans d'expérience sur des systèmes backend distribués, critiques et scalables en .NET/Python.",
  "Spécialisé dans la conception d'API REST, la Clean Architecture / DDD, les migrations cloud (IBM Cloud, AWS, Azure) et la mise en production de services backend scalables.",
  "Intégration IA appliquée : RAG, agents LLM multi-frameworks (CrewAI, LangChain), tool use, MCP — certifié Anthropic Academy (mai 2026) & NVIDIA Gen AI LLMs (2026). Projets livrés : SAIF-IA Chatbot, My Toyota, CV Critic Agent.",
];

export const profileEn = [
  "Software architect with 15+ years of experience designing distributed, critical, and scalable backend systems in .NET/Python.",
  "Specialised in REST API design, Clean/DDD architecture, cloud migrations (IBM Cloud, AWS, Azure), and production-grade scalable backend services.",
  "Applied AI integration: RAG, multi-framework LLM agents (CrewAI, LangChain), tool use, MCP — Anthropic Academy certified (May 2026) & NVIDIA Gen AI LLMs (2026). Projects delivered: SAIF-IA Chatbot, My Toyota, CV Critic Agent.",
];

// ─── Recruiter Summary ────────────────────────────────────────────────────────
export const recruiterSummary = {
  fr: {
    title: "⚡ Recruteur pressé ?",
    subtitle: "30 secondes pour tout comprendre",
    keySkills: [
      "C# / .NET (15+ ans d'expérience)",
      "Python — automatisation, data, IA appliquée",
      "Claude API (Anthropic) — Tool Use, Streaming, Structured Outputs, MCP",
      "RAG, LangChain, CrewAI — agents LLM multi-frameworks",
      "Architectures microservices & cloud (IBM Cloud, AWS, Azure, Kubernetes/Helm)",
      "Leadership technique — équipes jusqu'à 10 devs",
    ],
    topProjects: [
      { name: "SAIF-IA", desc: "Agent IA intégré au portfolio — 6 outils MCP, Claude Tool Use API, RAG pgvector, streaming SSE" },
      { name: "Resell Radar", desc: "Veille automatisée annonces publiques — Python, Playwright, Mistral LLM, Telegram" },
      { name: "Migration Cloud BNP Paribas AM", desc: "Migration applicative PaaS/IaaS IBM Cloud, équipe de 10 devs" },
    ],
    lookingFor: "Missions Architecte logiciel, Senior Backend .NET / Python ou Intégration IA — Paris / remote.",
  },
  en: {
    title: "⚡ In a hurry?",
    subtitle: "30 seconds to understand everything",
    keySkills: [
      "C# / .NET (15+ years of experience)",
      "Python — automation, data, AI",
      "Claude API (Anthropic) — Tool Use, Streaming, Structured Outputs, MCP",
      "RAG, LangChain, CrewAI — LLM agents multi-frameworks",
      "Microservices & Cloud architectures (IBM Cloud, AWS, Azure, Kubernetes/Helm)",
      "Technical leadership — teams up to 10 devs",
    ],
    topProjects: [
      { name: "SAIF-IA", desc: "Portfolio AI agent — 6 MCP tools, Claude Tool Use API, pgvector RAG, SSE streaming, parallel tools" },
      { name: "Resell Radar", desc: "Public listings monitoring — Python, Playwright, Mistral LLM, Telegram" },
      { name: "BNP Paribas AM Cloud Migration", desc: "PaaS/IaaS IBM Cloud migration, team of 10 devs" },
    ],
    lookingFor: "Software Architect, Senior Backend .NET / Python, or AI Integration missions — Paris / remote.",
  },
};

// ─── Experience ───────────────────────────────────────────────────────────────
export interface ExperienceSubSection {
  titleFr: string;
  titleEn: string;
  bulletsFr: string[];
  bulletsEn: string[];
}

export interface ExperienceItem {
  company: string;
  roleFr: string;
  roleEn: string;
  period: string;
  location: string;
  stack: string[];
  bulletsFr: string[];
  bulletsEn: string[];
  subSections?: ExperienceSubSection[];
  current?: boolean;
  phased?: boolean; // true = subSections sont des missions séquentielles (afficher [1][2][3])
}

export const experiences: ExperienceItem[] = [
  {
    company: "BNP Paribas Asset Management",
    roleFr: "Tech Lead & Architecte logiciel — Cloud / Microservices",
    roleEn: "Technical Lead & Software Architect — Cloud / Microservices",
    period: "Août 2022 → Présent",
    location: "Paris",
    stack: [".NET 6/8", "ASP.NET Core", "Python", "FastAPI", "Kafka", "PostgreSQL", "IBM Cloud", "Kubernetes", "Docker", "Helm", "Azure DevOps", "React", "TypeScript"],
    bulletsFr: [],
    bulletsEn: [],
    subSections: [
      {
        // Phase 1 — fusion Transformation Cloud + Backend Architecture
        titleFr: "Architecte Cloud & Transformation",
        titleEn: "Cloud & Transformation Architect",
        bulletsFr: [
          "Analyse des dépendances, impacts de migration et architectures cibles sur IBM Cloud",
          "Modernisation d'applications legacy vers microservices cloud-native ; migrations SQL Server → PostgreSQL Cloud",
          "Conception d'APIs REST, architectures événementielles Kafka, backends .NET 6/8 et Python FastAPI",
          "Optimisation des performances backend, orchestration de données multi-sources et cache multi-niveaux",
        ],
        bulletsEn: [
          "Dependencies analysis, migration impacts and target architectures on IBM Cloud",
          "Legacy modernisation towards cloud-native microservices; SQL Server → PostgreSQL Cloud migration",
          "REST APIs, Kafka event-driven architecture, .NET 6/8 and Python FastAPI backends",
          "Backend performance optimisation, multi-source data orchestration and multi-layer caching",
        ],
      },
      {
        // Phase 2 — Lead technique Sense
        titleFr: "Tech Lead — Plateforme Sense",
        titleEn: "Tech Lead — Sense Platform",
        bulletsFr: [
          "Sense — plateforme Multi Asset (7 microservices + front React, ~120 utilisateurs) — lead technique jusqu'à 10 personnes",
          "Coordination technique, résolution de blocages, revues de code backend et suivi inter-équipes",
          "Cadrage technique et suivi d'intégration du service AI/RAG documentaire (équipe dédiée) — définition des points de contact API",
        ],
        bulletsEn: [
          "Sense — Multi Asset platform (7 microservices + React front, ~120 internal users) — technical lead up to 10 people",
          "Technical coordination, blocker resolution, backend code reviews, and cross-team dependency tracking",
          "Technical framing and follow-up for the AI/RAG document service integrated into Sense (owned by a dedicated team) — API contract definition",
        ],
      },
      {
        // Phase 3 — Dev backend Jasmine (mission actuelle)
        titleFr: "Dev Backend — Projet Jasmine",
        titleEn: "Backend Dev — Jasmine Project",
        bulletsFr: [
          "Conception et développement d'un Data Service Python/FastAPI pour agréger, normaliser et préparer des données financières et de conformité",
          "Mise en place de flux REST/Kafka, traitements asynchrones et orchestration de données issues de multiples API",
          "Contribution backend Python, avec interventions ponctuelles .NET, sur une plateforme liée à l'intégration de portefeuilles externes",
        ],
        bulletsEn: [
          "Python FastAPI Data Service aggregating, normalising, and preparing financial and compliance data",
          "REST + Kafka flows, asynchronous processing, and orchestration across multiple APIs",
          "Python backend contribution, with occasional .NET work, on a platform supporting external portfolio integration",
        ],
      },
    ],
    current: true,
    phased: true,
  },
  {
    company: "Société Générale CIB — X-One",
    roleFr: "Senior Software Engineer",
    roleEn: "Senior Software Engineer",
    period: "Déc 2018 → Août 2022",
    location: "Paris",
    stack: ["C# .NET Core 2.2", ".NET 4.6/4.8", "WebAPI", "Jenkins", "Oracle", "Sybase", "PostgreSQL", "TDD", "BDD", "SonarQube", "Clean Architecture"],
    bulletsFr: [
      "Développeur senior sur X-One Back Office Equity, l'une des grandes plateformes trading de SG CIB (projet impliquant ~200 développeurs)",
      "Implémentation de modules en Clean Architecture / DDD — séparation Domain, Application et Infrastructure sur les nouveaux développements",
      "Optimisation de microservices et traitements batch — gain de performance d'environ 40% via optimisation d'index et parallélisation",
      "Industrialisation du socle de tests : TDD/BDD, migration Rhino Mocks vers Moq, réduction du temps d'exécution des tests d'environ 1h",
      "Modernisation technique .NET : migration de projets vers le format SDK Style, amélioration de la maintenabilité et suivi SonarQube",
      "Release manager / factory manager — coordination de 5+ équipes feature, planification des releases et suivi des dépendances inter-équipes",
    ],
    bulletsEn: [
      "Senior developer on X-One Back Office Equity, one of SG CIB's major trading platforms (project involving ~200 developers)",
      "Implemented modules using Clean Architecture / DDD — Domain, Application, and Infrastructure separation on new developments",
      "Optimised microservices and batch processing — ~40% performance gain through index optimisation and parallelisation",
      "Industrialised the test foundation: TDD/BDD, Rhino Mocks to Moq migration, and test execution time reduced by ~1 hour",
      "Modernised the .NET codebase: migration to SDK-style projects, maintainability improvements, and SonarQube follow-up",
      "Release manager / factory manager — coordinated 5+ feature teams, release planning, and cross-team dependency tracking",
    ],
  },
  {
    company: "BNP Paribas Asset Management",
    roleFr: "BA & Développeur .NET — Rôle Hybride",
    roleEn: "BA & .NET Developer — Hybrid Role",
    period: "Sep 2016 → Déc 2018",
    location: "Paris",
    stack: [".NET", "C#", "TDD", "NUnit", "Oracle SQL", "UML", "BPMN"],
    bulletsFr: [
      "Rôle hybride : Business Analyst / Développeur .NET / Application Owner",
      "Développement full-stack et gestion des exigences métier",
      "Ownership technique de projets — interface entre équipes métier et IT",
      "Modélisation UML/BPMN et rédaction de spécifications fonctionnelles",
    ],
    bulletsEn: [
      "Hybrid role: Business Analyst / .NET Developer / Application Owner",
      "Full-stack development + business requirements management",
      "Technical ownership of projects — interface between business and IT teams",
      "UML/BPMN modelling, functional specification writing",
    ],
  },
  {
    company: "Société Générale Securities Services (SGSS)",
    roleFr: "Ingénieur Développement",
    roleEn: "Software Engineer",
    period: "Fév 2013 → Août 2016",
    location: "Paris",
    stack: ["C#", "ASP.NET", "WCF", "Oracle", "PL/SQL", "ETL", "REST", "OAuth 2.0"],
    bulletsFr: [],
    bulletsEn: [],
    subSections: [
      {
        titleFr: "Équipe Gallery — Fund Administration (Mar 2014 → Août 2016)",
        titleEn: "Gallery Team — Fund Administration (Mar 2014 → Aug 2016)",
        bulletsFr: [
          "Maintenance et évolution d'une application de Fund Administration (reporting, NAV, GED)",
          "Développement de web services inter-applicatifs (WCF, ASMX)",
          "Intégration ETL multi-pays pour le reporting",
          "Implémentation de clients REST OAuth 2.0",
        ],
        bulletsEn: [
          "Fund Administration application maintenance and evolution (reporting, NAV, DMS)",
          "Inter-application web service development (WCF, ASMX)",
          "Multi-country ETL integration for reporting",
          "REST client OAuth 2.0 implementation",
        ],
      },
      {
        titleFr: "Équipe Glass Custody (Fév 2013 → Mar 2014)",
        titleEn: "Glass Custody Team (Feb 2013 → Mar 2014)",
        bulletsFr: [
          "Maintenance GCU (Glass Custody Unit) et Glass Admin",
          "Corrections et évolutions sur base Oracle / PL/SQL",
          "Réplication de données Oracle Jobs, import/export",
        ],
        bulletsEn: [
          "GCU (Glass Custody Unit) and Glass Admin maintenance",
          "Bug fixes and evolutions on Oracle / PL-SQL base",
          "Oracle Jobs data replication, import/export",
        ],
      },
    ],
  },
  {
    company: "Stanhome IT",
    roleFr: "Développeur Web C#/.NET",
    roleEn: "C#/.NET Web Developer",
    period: "Oct 2012 → Jan 2013",
    location: "France",
    stack: ["C# .NET", "ASP.NET", "SQL Server"],
    bulletsFr: [],
    bulletsEn: [],
  },
];

// ─── Skills ───────────────────────────────────────────────────────────────────
export interface SkillGroup {
  categoryFr: string;
  categoryEn: string;
  icon: string;
  highlight?: boolean;
  skills: { name: string; level?: number }[];
}

export const skillGroups: SkillGroup[] = [
  {
    categoryFr: "Backend & Architecture",
    categoryEn: "Backend & Architecture",
    icon: "server",
    skills: [
      { name: "C# / .NET", level: 95 },
      { name: "Python", level: 85 },
      { name: "FastAPI", level: 80 },
      { name: "ASP.NET Core / WebAPI", level: 92 },
      { name: "Entity Framework Core", level: 88 },
      { name: "REST APIs", level: 93 },
      { name: "Microservices", level: 87 },
      { name: "Clean Architecture / DDD", level: 85 },
    ],
  },
  {
    categoryFr: "IA & LLM",
    categoryEn: "AI & LLM",
    icon: "brain",
    highlight: true,
    skills: [
      { name: "Claude API (Anthropic)", level: 88 },
      { name: "CrewAI (agents, tasks, crews, LiteLLM)", level: 80 },
      { name: "Tool Use", level: 85 },
      { name: "RAG (pgvector + OpenAI Embeddings + Supabase)", level: 87 },
      { name: "LangChain (document loaders, splitters, embeddings)", level: 78 },
      { name: "MCP", level: 78 },
      { name: "Prompt engineering avancé", level: 85 },
      { name: "Streaming & Structured Outputs", level: 83 },
      { name: "Mistral / OpenAI API", level: 83 },
      { name: "Chatbots (Telegram, WhatsApp)", level: 84 },
    ],
  },
  {
    categoryFr: "Data",
    categoryEn: "Data",
    icon: "database",
    skills: [
      { name: "SQL (Oracle / PostgreSQL / SQL Server)", level: 88 },
      { name: "PL/SQL", level: 82 },
      { name: "pandas / ETL", level: 84 },
      { name: "Reporting automatisé / BI", level: 80 },
    ],
  },
  {
    categoryFr: "Cloud / DevOps",
    categoryEn: "Cloud / DevOps",
    icon: "git-branch",
    skills: [
      { name: "Docker", level: 82 },
      { name: "Kubernetes / Helm", level: 75 },
      { name: "IBM Cloud", level: 75 },
      { name: "AWS (EC2, S3, Lambda)", level: 68 },
      { name: "Azure (App Service, AKS, Blob)", level: 72 },
      { name: "CI/CD", level: 80 },
      { name: "Azure DevOps / Jenkins", level: 80 },
      { name: "Git", level: 90 },
    ],
  },
  {
    categoryFr: "Frontend",
    categoryEn: "Frontend",
    icon: "monitor",
    skills: [
      { name: "TypeScript", level: 78 },
      { name: "React / Next.js", level: 75 },
      { name: "JavaScript", level: 78 },
    ],
  },
  {
    categoryFr: "Méthodes",
    categoryEn: "Methods",
    icon: "users",
    skills: [
      { name: "TDD / BDD (NUnit / XUnit / Moq)", level: 85 },
      { name: "Scrum / Kanban / SAFe", level: 88 },
      { name: "Code Review / Pair Programming", level: 90 },
    ],
  },
];

// ─── Projects ─────────────────────────────────────────────────────────────────
export interface Project {
  name: string;
  descFr: string;
  descEn: string;
  stack: string[];
  highlights: { fr: string; en: string }[];
  github?: string;
  liveUrl?: string;
  specUrl?: string;
  docs?: { labelFr: string; labelEn: string; url: string }[];
  featured?: boolean;
}

export const projects: Project[] = [
  // ── 1. Flagship — in production, most complete ────────────────────────────
  {
    name: "SAIF-IA Chatbot",
    descFr: "Agent IA intégré au portfolio, en production : 6 outils MCP, boucle agentique Claude Tool Use API, streaming SSE token par token, RAG pgvector et exécution parallèle des outils. Qualifie les recruteurs, adapte le pitch et filtre les ESN/SSII automatiquement.",
    descEn: "Production portfolio AI agent: 6 MCP tools, Claude Tool Use API agentic loop, token-by-token SSE streaming, pgvector RAG, and parallel tool execution. Qualifies recruiters, adapts the pitch, and filters agencies automatically.",
    stack: ["Next.js 16", "TypeScript", "Claude Haiku", "Groq", "Tool Use API", "SSE Streaming", "RAG pgvector", "OpenAI Embeddings", "Supabase", "Vercel"],
    highlights: [
      { fr: "6 outils MCP : search_knowledge (RAG sémantique), search_cv, get_github_repos, analyze_github_repo, web_research_recruiter (3 niveaux : statique + appel Claude dédié), schedule_meeting", en: "6 MCP tools: search_knowledge (semantic RAG), search_cv, get_github_repos, analyze_github_repo, web_research_recruiter (3 tiers: static + Claude sub-call), schedule_meeting" },
      { fr: "Streaming SSE token par token, exécution parallèle des outils (Promise.all) et routage multi-LLM (Groq pour la vitesse, Claude Haiku pour le raisonnement)", en: "Token-by-token SSE streaming + parallel tool execution (Promise.all) + multi-LLM routing (Groq speed / Claude Haiku intelligence)" },
      { fr: "RAG pgvector : 20 chunks Supabase + index HNSW + OpenAI text-embedding-3-small — qualification recruteur en 3 niveaux avec fallback Claude", en: "pgvector RAG: 20 Supabase chunks + HNSW index + OpenAI text-embedding-3-small — recruiter qualification in 3 tiers with Claude sub-call fallback" },
    ],
    liveUrl: "https://cv.saifallah.dev",
    docs: [
      { labelFr: "Fiche technique", labelEn: "Technical sheet", url: "/docs/saif-ia-technique.html" },
      { labelFr: "Manuel d'utilisation", labelEn: "User guide", url: "/docs/saif-ia-manuel.html" },
    ],
    featured: true,
  },
  // ── 2. Deployed, RAG + LangChain ─────────────────────────────────────────
  {
    name: "My Toyota",
    descFr: "Assistant RAG conversationnel pour manuels Toyota : questions en langage naturel, réponses extraites du PDF officiel et schémas techniques affichés en temps réel. Streaming SSE token par token.",
    descEn: "Conversational RAG assistant for Toyota manuals: natural language questions, answers extracted from the official PDF with real-time technical diagrams. Token-by-token SSE streaming.",
    stack: ["Next.js 16", "TypeScript", "Claude Haiku", "LangChain", "OpenAI Embeddings", "Supabase pgvector", "Supabase Storage", "PyMuPDF", "Python", "Vercel"],
    highlights: [
      { fr: "RAG pgvector HNSW : 1 740 chunks + capture PNG de chaque page PDF (1.5× zoom) — résout le problème des diagrammes vectoriels Toyota", en: "pgvector HNSW RAG: 1,740 chunks + PNG screenshot of each PDF page (1.5× zoom) — solves the Toyota vector diagram extraction problem" },
      { fr: "Streaming SSE (delta / sources / images / done) + galerie cliquable des schémas techniques avec lightbox", en: "SSE streaming (delta / sources / images / done) + clickable technical diagram gallery with lightbox" },
      { fr: "Pipeline d'ingestion migré vers LangChain (PyMuPDFLoader · RecursiveCharacterTextSplitter · OpenAIEmbeddings) — héritage automatique des métadonnées, splitter hiérarchique", en: "Ingestion pipeline migrated to LangChain (PyMuPDFLoader · RecursiveCharacterTextSplitter · OpenAIEmbeddings) — automatic metadata inheritance, hierarchical splitter" },
    ],
    github: "https://github.com/Sayfouche/my-toyota",
    liveUrl: "https://my-toyota-iota.vercel.app",
    docs: [
      { labelFr: "Fiche technique", labelEn: "Technical sheet", url: "https://my-toyota-iota.vercel.app/docs/TECHNICAL.html" },
      { labelFr: "Guide utilisateur", labelEn: "User guide", url: "https://my-toyota-iota.vercel.app/docs/GUIDE_UTILISATEUR.html" },
    ],
    featured: true,
  },
  // ── 3. Dual implementation, versioned reports ─────────────────────────────
  {
    name: "CV Critic Agent",
    descFr: "Workflow IA interne d'audit du CV — migré de Node.js/Anthropic SDK vers CrewAI (Python) : 3 agents (Global Critic · Printable CV Critic · Strategy), roles/backstories formalisés, injection de contexte inter-tâches, rapports versionnés.",
    descEn: "Internal AI CV audit workflow — migrated from Node.js/Anthropic SDK to CrewAI (Python): 3 agents (Global Critic · Printable CV Critic · Strategy), formalised roles/backstories, inter-task context injection, versioned reports.",
    stack: ["CrewAI", "Python", "LiteLLM", "Node.js", "Claude API", "Prompt Engineering", "Markdown Reports", "Versioned Outputs"],
    highlights: [
      { fr: "Migration orchestration Node.js → CrewAI Python : mêmes 3 agents, rôles/backstories formalisés, context passing automatique via CrewAI", en: "Node.js → CrewAI Python orchestration migration: same 3 agents, formalised roles/backstories, automatic context passing via CrewAI" },
      { fr: "Critics intentionnellement indépendants (pas de context= entre eux) — seul le Strategy Agent lit les deux outputs", en: "Critics intentionally independent (no context= between them) — only the Strategy Agent reads both outputs" },
      { fr: "Rapports datés + latest/ pour suivre les itérations · deux commandes npm : critique-cv (Node.js) et critique-cv-crew (CrewAI)", en: "Timestamped reports + latest/ to track iterations · two npm commands: critique-cv (Node.js) and critique-cv-crew (CrewAI)" },
    ],
    docs: [
      { labelFr: "Fiche technique", labelEn: "Technical sheet", url: "/docs/cv-critic-technique.html" },
      { labelFr: "Manuel d'utilisation", labelEn: "User guide", url: "/docs/cv-critic-manuel.html" },
    ],
    featured: true,
  },
  // ── 4. Functional, live Telegram alerts ──────────────────────────────────
  {
    name: "Resell Radar",
    descFr: "Système de veille automatisée pour annonces publiques de seconde main : scoring IA des opportunités, alertes Telegram et aide à la négociation.",
    descEn: "Automated monitoring system for public second-hand listings: AI opportunity scoring, Telegram alerts, and negotiation assistance.",
    stack: ["Python", "Playwright", "Mistral LLM", "Telegram API", "SQLite", "APScheduler"],
    highlights: [
      { fr: "Collecte contrôlée d'annonces publiques, avec logique de respect des limites et des usages raisonnables", en: "Controlled collection of public listings with rate limits and reasonable-use safeguards" },
      { fr: "Scoring IA des opportunités : marge, état, marque, liquidité et priorité d'action", en: "AI opportunity scoring: margin, condition, brand, liquidity, and action priority" },
      { fr: "~7 alertes Telegram par cycle de 15 min — génération assistée de messages de négociation via Mistral LLM", en: "~7 Telegram alerts per 15-min cycle — assisted negotiation message generation via Mistral LLM" },
    ],
    github: "https://github.com/Sayfouche/resell-radar",
    docs: [
      { labelFr: "Fiche technique", labelEn: "Technical sheet", url: "/docs/resell-radar-technique.html" },
      { labelFr: "Manuel d'utilisation", labelEn: "User guide", url: "/docs/resell-radar-manuel.html" },
    ],
    featured: true,
  },
  // ── 5. Phase 1 scaffold — in progress ────────────────────────────────────
  {
    name: "Elyne lit",
    descFr: "Coach de lecture assisté par IA, en temps réel, pour enfants — transcription ASR, évaluation phonémique et correction de prononciation (ex. : 'oi', 'eau') avec explication pédagogique vocale. Créé pour Elyne, 6 ans.",
    descEn: "Real-time AI reading coach for children — ASR transcription, phoneme-level assessment, pronunciation correction with spoken pedagogical feedback. Built for Elyne, age 6.",
    stack: ["Next.js", "FastAPI", "WebSocket", "Faster-Whisper", "wav2vec2", "Silero VAD", "edge-tts", "Python", "HuggingFace"],
    highlights: [
      { fr: "Pipeline temps réel sous 500ms : Silero VAD → Faster-Whisper → wav2vec2 → Claude Haiku → edge-tts", en: "Real-time pipeline under 500ms: Silero VAD → Faster-Whisper → wav2vec2 → Claude Haiku → edge-tts" },
      { fr: "Détection phonémique ciblée en français — 'oi' /wa/, 'eau' /o/, 'an' /ɑ̃/, 'eu' /ø/...", en: "Targeted French phoneme detection — 'oi' /wa/, 'eau' /o/, 'an' /ɑ̃/, 'eu' /ø/..." },
      { fr: "Interface enfant ludique : surlignage mot courant, bulle de correction audio, étoiles de progression", en: "Child-friendly UI: current word highlight, audio correction bubble, progress stars" },
    ],
    docs: [
      { labelFr: "Fiche technique", labelEn: "Technical sheet", url: "/docs/elyne-lit-technique.html" },
      { labelFr: "Manuel d'utilisation", labelEn: "User guide", url: "/docs/elyne-lit-manuel.html" },
    ],
    featured: true,
  },
  // ── 6. Blog — 1 article, en développement ────────────────────────────────
  {
    name: "Saifallah Blog",
    descFr: "Blog technique personnel consacré à l'IA appliquée, aux architectures RAG, au cloud et aux systèmes logiciels. Premier article : guide RAG / LLM / NVIDIA / AWS / Azure.",
    descEn: "Personal technical blog for long-form articles on applied AI, RAG architectures, cloud, and software systems. First article: RAG / LLM / NVIDIA / AWS / Azure guide.",
    stack: ["Next.js 16", "TypeScript", "Technical Writing", "RAG", "LLM Architecture", "Vercel"],
    highlights: [
      { fr: "Article fondateur adapté d'un draft complet de 545 lignes sur l'écosystème RAG / LLM / inference serving", en: "Foundational article adapted from a 545-line draft on the RAG / LLM / inference serving ecosystem" },
      { fr: "Positionnement public complémentaire au CV : contenu technique, pédagogie et visibilité LinkedIn", en: "Public positioning complementing the CV: technical content, pedagogy, and LinkedIn visibility" },
      { fr: "Préparé pour déploiement sur blog.saifallah.dev", en: "Prepared for deployment on blog.saifallah.dev" },
    ],
    liveUrl: "https://blog.saifallah.dev",
    featured: false,
  },
];

// ─── Certifications ───────────────────────────────────────────────────────────
export const certifications = [
  {
    nameFr: "Claude with the Anthropic API",
    nameEn: "Claude with the Anthropic API",
    issuer: "Anthropic Academy",
    year: "Mai 2026",
    statusFr: "Obtenue",
    statusEn: "Certified",
    credentialId: "5n8hrz4jowy6",
    verifyUrl: "https://verify.skilljar.com/c/5n8hrz4jowy6",
    badgeImage: "/certifications/certif_anthropic_academy.svg" as string | undefined,
    theme: "violet" as "violet" | "nvidia",
    topicsFr: [
      "Building with the Claude API",
      "Claude Code 101",
      "Claude Code in Action",
      "Introduction to agent skills",
      "Introduction to Model Context Protocol",
      "Model Context Protocol — Advanced Topics",
      "AI Fluency — Framework & Foundations",
      "AI Fluency for Small Businesses",
      "Tool Use / Function Calling",
      "Streaming, Structured Outputs, RAG, MCP",
    ],
    topicsEn: [
      "Building with the Claude API",
      "Claude Code 101",
      "Claude Code in Action",
      "Introduction to agent skills",
      "Introduction to Model Context Protocol",
      "Model Context Protocol — Advanced Topics",
      "AI Fluency — Framework & Foundations",
      "AI Fluency for Small Businesses",
      "Tool Use / Function Calling",
      "Streaming, Structured Outputs, RAG, MCP",
    ],
  },
  {
    nameFr: "NVIDIA Certified Associate — Gen AI LLMs",
    nameEn: "NVIDIA Certified Associate — Gen AI LLMs",
    issuer: "NVIDIA",
    year: "2026",
    statusFr: "Obtenue",
    statusEn: "Completed",
    credentialId: "e32458aa-0f0f-42be-bf4f-95128ea5f29e",
    verifyUrl: "https://www.credly.com/badges/e32458aa-0f0f-42be-bf4f-95128ea5f29e",
    badgeImage: "/certifications/certif_nvidia_genai_llm.png" as string | undefined,
    theme: "nvidia" as "violet" | "nvidia",
    topicsFr: [
      "Fondamentaux LLM — architecture Transformer, tokenisation",
      "RAG — Retrieval-Augmented Generation, chunking, vector search",
      "Fine-tuning & PEFT — LoRA, QLoRA, instruction tuning",
      "Inférence & serving — TensorRT-LLM, NVIDIA NIM",
      "Guardrails & sécurité — NeMo Guardrails, alignment",
      "Agents LLM — tool use, orchestration, frameworks",
      "Évaluation — métriques faithfulness, relevance, hallucination",
    ],
    topicsEn: [
      "LLM Fundamentals — Transformer architecture, tokenisation",
      "RAG — Retrieval-Augmented Generation, chunking, vector search",
      "Fine-tuning & PEFT — LoRA, QLoRA, instruction tuning",
      "Inference & serving — TensorRT-LLM, NVIDIA NIM",
      "Guardrails & safety — NeMo Guardrails, alignment",
      "LLM Agents — tool use, orchestration, frameworks",
      "Evaluation — faithfulness, relevance, hallucination metrics",
    ],
  },
];

// ─── Education ────────────────────────────────────────────────────────────────
export const education = [
  {
    degreeFr: "Diplôme d'Ingénieur Informatique",
    degreeEn: "Software Engineering Degree",
    school: "ENSI — École Nationale des Sciences de l'Informatique",
    year: "2011",
  },
];

// ─── Languages ────────────────────────────────────────────────────────────────
export const languages = [
  { nameFr: "Français", nameEn: "French", levelFr: "Courant", levelEn: "Fluent" },
  { nameFr: "Anglais", nameEn: "English", levelFr: "Courant professionnel", levelEn: "Professional fluency" },
  { nameFr: "Arabe", nameEn: "Arabic", levelFr: "Langue maternelle", levelEn: "Native" },
];

// ─── Nav labels ───────────────────────────────────────────────────────────────
export const navItems = [
  { id: "recruiter", labelFr: "Recruteur pressé", labelEn: "Quick Summary" },
  { id: "experience", labelFr: "Expériences", labelEn: "Experience" },
  { id: "skills", labelFr: "Compétences", labelEn: "Skills" },
  { id: "projects", labelFr: "Projets", labelEn: "Projects" },
  { id: "contact", labelFr: "Contact", labelEn: "Contact" },
];

export const navLabels = {
  fr: {
    recruiter: "Recruteur pressé",
    experience: "Expériences",
    skills: "Compétences",
    projects: "Projets",
    contact: "Contact",
    downloadCV: "Télécharger CV",
    toggleLang: "EN",
  },
  en: {
    recruiter: "Quick Summary",
    experience: "Experience",
    skills: "Skills",
    projects: "Projects",
    contact: "Contact",
    downloadCV: "Download CV",
    toggleLang: "FR",
  },
};
