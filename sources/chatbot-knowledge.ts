// Server-side only — never imported by client components
// Fill in real values before deploying

export const knowledge = {
  contact: {
    phone: process.env.CONTACT_PHONE ?? "+33 7 81 •• •• ••",
    email: "mansour.saifallah@gmail.com",
    linkedin: "https://www.linkedin.com/in/sa%C3%AFfallah-mansour-18078525/",
    availability: "Disponible avec 1 mois de préavis",
    location: "Paris — remote partiel possible",
    tjm: "À discuter selon le contexte de la mission",
  },

  missions: {
    bnppam_current: `
BNP Paribas Asset Management (Août 2022 → Présent) — détails supplémentaires :
Contexte :
- Mission dans un programme de transformation du SI, modernisation applicative et migration progressive d'applications on-premise vers IBM Cloud
- Intervention initiale comme Senior Software Engineer, puis évolution vers Technical Lead avec responsabilités d'architecture applicative, coordination technique et accompagnement des équipes
- Domaine Asset Management : applications utilisées par analystes financiers, équipes Multi Asset, gestion portefeuille, conformité et investissement
- Applications critiques : outils de recherche/analyse financière, plateformes de gestion et conformité portefeuille, services liés à l'intégration de portefeuilles externes

Transformation cloud & modernisation :
- Études de migrabilité d'applications existantes, analyse des dépendances techniques et impacts de migration
- Participation à la définition d'architectures cibles cloud-native sur IBM Cloud
- Modernisation d'applications legacy vers microservices
- Migration de bases SQL Server vers PostgreSQL Cloud ; participation à des études Oracle vers PostgreSQL
- Environnement : IBM Cloud, IKS, IBM COS, IBM Event Streams Kafka, IBM PostgreSQL Cloud, Docker, Helm, Azure DevOps, CI/CD YAML, Vault, SonarQube, Fortify

Leadership technique — Application Sense :
- Lead technique officiel sur Sense, plateforme Multi Asset pour analystes internes
- Coordination d'un périmètre allant jusqu'à environ 10 personnes, puis rôle de référent technique sur un noyau réduit d'environ 3 personnes
- Sense permet la consultation de données financières, l'analyse d'instruments, l'accès ratings/research, l'aide à la décision d'investissement et le partage d'analyses métier
- Sense contient aussi un service récent d'IA documentaire de type RAG : les analystes peuvent joindre ou exploiter des documents, notes et thèses d'analyse, puis poser des questions sur leur contenu
- Formulation honnête obligatoire : Saïfallah a participé à l'étude et au suivi du service AI/RAG documentaire de Sense (porté par une équipe dédiée). Il ne doit pas revendiquer l'implémentation. Formulation autorisée : "J'ai participé à l'étude et suivi le projet du service AI/RAG intégré à Sense — c'est une exposition professionnelle concrète à un cas d'usage IA en Asset Management."
- Responsabilités : coordination technique, résolution de blocages, validation des choix d'implémentation, code reviews backend, accompagnement front/back, cadrage technique des besoins métier, suivi des dépendances inter-équipes, pilotage technique

Backend & architecture microservices :
- Conception et développement de microservices backend REST et event-driven
- Stack : Python FastAPI, AsyncIO, HTTPX, Pytest, Pytest-AsyncIO, .NET 6/8, ASP.NET Core, SignalR, Kafka, PostgreSQL, SQL Server, Oracle, React/TypeScript
- Sujets : APIs REST, traitements asynchrones, orchestration de données, batch processing, optimisation performances backend, cache mémoire et cache COS

Projet stratégique Jasmine :
- Plateforme stratégique construite pour l'intégration de portefeuilles externes
- Architecture microservices, communication REST + Kafka, backends Python FastAPI et .NET, frontend React/TypeScript, Kubernetes IBM Cloud
- Contribution principale : développement backend Python du Data Service, avec interventions ponctuelles .NET
- Rôle du Data Service : récupérer données financières et conformité, agréger données de multiples systèmes, préparer données pour services de calcul, orchestrer traitements techniques, mapper et normaliser données métier
- Responsabilités : gestion des flux Kafka, cache multi-niveaux, optimisation backend, batchs et traitements asynchrones, participation à l'architecture microservices

Angle tactique SAIF-IA :
- Ne pas vendre cette mission comme une mission IA personnelle de bout en bout. La vendre comme une mission architecture/cloud/data sur Sense, application qui contient aussi un cas d'usage AI/RAG documentaire réel
- Message clé : Saïfallah sait faire passer des applications critiques vers des architectures cloud-native et microservices dans un SI bancaire exigeant ; son exposition au service AI/RAG documentaire de Sense renforce la cohérence de sa transition vers IA appliquée
    `.trim(),

    sgcib: `
Société Générale CIB — X-One (Déc 2018 → Août 2022) — détails supplémentaires :
- Projet de 200+ développeurs, one of the biggest trading platforms in SG CIB
- Contribution principale : optimisation microservices, réduction des temps de traitement batch de 40%
- Release manager : coordination entre 5+ équipes feature, planification des releases
- Mise en place Clean Architecture sur les nouveaux modules (séparation Domain/Application/Infrastructure)
- Mentor junior developers, pair programming régulier
    `.trim(),

    bnppam_2016_2018: `
BNP Paribas Asset Management (Sep 2016 → Déc 2018) — détails supplémentaires :
- Rôle hybride unique : à la fois Business Analyst et développeur .NET — interface directe avec le métier (Front Office, Middle Office)
- Application owner sur 2 applications critiques de reporting réglementaire
- Rédaction de specs fonctionnelles détaillées (UML/BPMN), coordination MOE/MOA
    `.trim(),

    sgss: `
SGSS — Société Générale Securities Services (Fév 2013 → Août 2016) :
- Équipe Gallery (Fund Admin) : application de reporting NAV/GED pour 100+ fonds d'investissement
- Équipe Glass Custody : maintenance base Oracle PL/SQL critique pour la custodisation
- Première expérience en finance de marché, culture craftsmanship
    `.trim(),
  },

  workStyle: `
Style de travail et valeur ajoutée :
- Très autonome : capable de prendre en main un projet complexe avec peu de contexte initial
- Communication claire entre métier et tech : habitué aux rôles hybrides BA/Dev
- Rigueur technique : TDD/BDD quand le contexte le justifie, code review exigeant mais bienveillant
- Curieux et en veille constante sur l'IA (formation Anthropic Academy, projets perso actifs)
- Préfère les projets à fort impact métier sur les projets "usine à fonctionnalités"
- À l'aise en leadership technique sans vouloir basculer full management
  `.trim(),

  positioning: `
Positionnement cible :
- Architecte logiciel — Intégration IA (titre court CV)
- Variantes acceptées : Architecte Software, Tech Lead Backend, Senior .NET/Python
- 15+ ans d'expérience depuis le début de carrière post-diplôme 2011
- Socle principal : architecture logicielle, backend .NET/Python, APIs, cloud, sécurité, systèmes critiques finance
- Cloud & DevOps : IBM Cloud (principal, BNP AM), Kubernetes / Helm (IKS BNP), AWS (EC2, S3, Lambda — projets personnels et études), Azure (App Service, AKS, Blob Storage — Azure DevOps utilisé en CI/CD BNP)
- Spécialisation IA récente et concrète : RAG, agents LLM, tool use, MCP, agents de qualification, intégration produit
- Ne jamais présenter les anciennes missions professionnelles comme des missions IA si ce n'était pas le cas
- Angle fort : Saïfallah sait industrialiser l'IA parce qu'il vient du monde des systèmes fiables, pas seulement des prototypes
  `.trim(),

  certificationPlan: `
Certifications IA :
- Obtenues : Anthropic Academy — Building with the Claude API, Claude Code 101, Claude Code in Action, Introduction to agent skills, Introduction to Model Context Protocol, Model Context Protocol Advanced Topics, AI Fluency Framework & Foundations, AI Fluency for Small Businesses
- En cours / objectif court terme : Microsoft AI Solution Lead, orientation executive/business et architecture de solutions IA
- En cours / objectif court terme : NVIDIA Generative AI / LLM, orientation GenAI engineering et compréhension des modèles
- Planifiée : AWS AI Practitioner, pour compléter la vision cloud IA multi-provider

Lecture tactique :
- Sur le CV public, rester sobre : afficher obtenu et éventuellement en cours, sans surcharger
- En conversation, expliquer la cohérence : Anthropic pour l'intégration LLM, Microsoft pour la vision solution/business, NVIDIA pour GenAI/LLM, AWS pour le socle cloud IA
- Ne pas vendre ces certifications planifiées comme déjà acquises
- Réponse au risque "il se forme, pas expert" : assumer que les certifications planifiées ne sont pas la preuve principale. La preuve principale reste 15+ ans d'architecture logicielle, le delivery cloud/microservices en SI critique, les projets IA concrets et la certification Anthropic déjà obtenue
  `.trim(),

  projectPositioning: `
Positionnement des projets IA :
- SAIF-IA Chatbot est le projet public de portfolio. Son objectif est commercial/recruteur : qualifier, présenter, adapter le discours et orienter vers le contact.
- CV Critic Agent est un agent interne distinct, extrait dans un repo autonome. Son objectif est volontairement opposé : critiquer le CV, détecter les faiblesses, challenger la crédibilité IA et générer des rapports versionnés.
- CV Critic Agent démontre une migration technique complète : orchestration Node.js manuelle avec Anthropic SDK → script Python CrewAI → projet CrewAI native autonome, avec refactoring des prompts/sources/rapports, provider Mistral par défaut et tests de non-régression mock.
- Ne pas mélanger SAIF-IA et CV Critic : l'un vend intelligemment, l'autre critique durement pour améliorer le positionnement.
- Resell Radar doit être présenté prudemment comme veille automatisée d'annonces publiques et scoring IA. Ne jamais le vendre comme scraping agressif ou contournement de plateformes.
- Pour Resell Radar, insister sur collecte contrôlée, respect des limites, usages raisonnables, scoring métier, alerting et aide à la décision.
  `.trim(),

  idealMission: `
Mission idéale :
- Architecte Software, Senior Backend .NET/Python, Lead Tech, ou Intégration IA
- Secteur : finance de marché, fintech, IA, tech produit
- Localisation : Paris IDF — remote partiel bienvenu, full remote selon le projet
- Durée : mission longue durée préférée (6 mois+)
- Environnement : équipe technique de qualité, product ownership clair, pas de mode pompier permanent
  `.trim(),

  ssiiResponse:
    "Merci pour l'intérêt. Le plus simple est de partager le contexte de mission, l'équipe, la durée et le mode de collaboration envisagé.",

  faq: {
    disponibilite: "Disponible avec 1 mois de préavis.",
    remote: "Remote partiel idéal. Full remote possible selon le projet.",
    tjm: "TJM à discuter selon le contexte, la durée et le type de mission.",
    relocation: "Basé à Paris, pas de relocalisation.",
    secteurs: "Finance de marché, fintech, IA, tech produit en priorité.",
  },
};
