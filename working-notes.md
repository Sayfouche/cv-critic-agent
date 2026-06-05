# Working Notes — CV Portfolio

Derniere mise a jour : 2026-05-15

## Mode de travail

- Travailler par increments fermes.
- Eviter de relancer `npm run critique-cv` apres chaque micro-changement.
- Relancer `npm run lint` apres modifications de code/TSX.
- Relancer `npm run build` seulement apres un bloc fonctionnel complet.
- Relancer `npm run critique-cv` seulement apres un increment editorial significatif.
- Lire seulement les sections utiles des rapports : verdict, actions prioritaires, questions ouvertes.

## Positionnement valide

- Positionnement cible : Architecte Solution Software + IA appliquee.
- Experience affichee : 15+ ans.
- Ne pas presenter les anciennes missions comme des missions IA si ce n'est pas vrai.
- Angle narratif : socle architecture/backend/cloud/data critique -> specialisation IA appliquee.

## Decisions validees

- SAIF-IA = chatbot public de portfolio.
  - Objectif : qualifier, presenter, orienter, convertir.
  - Ne pas le confondre avec CV Critic.
- CV Critic Agent = agent interne.
  - Objectif : critiquer, challenger, detecter les risques de perception.
  - Rapports : global, printable-cv, strategy.
- Strategy Agent lit `context.md`; les critiques globales ne lisent pas le contexte interne.
- Resell Radar doit etre presente comme veille automatisee d'annonces publiques + scoring IA, pas comme scraping agressif.
- Sense peut etre mentionne comme application contenant aussi un service AI/RAG documentaire.
  - SAIF-IA ne doit jamais dire ou laisser entendre que Saifallah a implemente ce service AI/RAG.
- Sense : lead technique officiel, perimetre jusqu'a environ 10 personnes, puis referent technique sur noyau reduit d'environ 3 personnes.
- Sense AI/RAG : suivi d'etude et integration autour du service, pas implementation complete revendiquee.
- Jasmine : developpement backend Python principalement, interventions ponctuelles .NET.
- Confidentialite : ne pas mentionner AXA IM ; utiliser "portefeuilles externes".
- Certifications Anthropic Academy : parcours considere complete en mai 2026.

## Etat actuel implemente

- Google Fonts retire.
- `npm run lint` OK au dernier check.
- `npm run build` OK au dernier check apres modifications Sense/Jasmine/confidentialite.
- SAIF-IA Chatbot lie a une fiche technique publique :
  - `/technical-sheets/saif-ia-technical-sheet.md`
- Fiche technique `CV Critic & Strategy Agent` creee :
  - `/technical-sheets/cv-critic-strategy-agent.md`
- CV imprimable contient une section `Trajectoire IA appliquee`.
- CV imprimable contient une section `Projets IA appliques`.
- Agent critique multi-rapports :
  - `agents/cv-critic/reports/latest/global.md`
  - `agents/cv-critic/reports/latest/printable-cv.md`
  - `agents/cv-critic/reports/latest/strategy.md`
- Plan interne de certifications IA cree :
  - `docs/AI_CERTIFICATION_PLAN.md`
  - Statut : prive, non affiche sur site/CV tant que les certifications ne sont pas obtenues.
  - Certifications ciblees : AWS Certified AI Practitioner, IBM AI Developer Professional Certificate, NVIDIA-Certified Associate: Generative AI LLMs, AI For Business Specialization Wharton/Penn, Microsoft Certified: AI Transformation Leader, Microsoft Certified: Machine Learning Operations (MLOps) Engineer Associate (beta), PMI Certified Professional in Managing AI, Salesforce Certified Agentforce Specialist.

## Prochaines priorites

1. Collecter des informations factuelles sur BNP/Sense/Jasmine.
   - role exact sur Sense ;
   - taille equipe ;
   - duree lead tech ;
   - scope apps/services cloud ;
   - role exact sur Jasmine Data Service ;
   - chiffres disponibles ou estimations prudentes.
2. Ameliorer le CV imprimable a partir des donnees BNP et des fiches techniques.
3. Eventuellement creer une fiche technique `Resell Radar`, avec formulation prudente.
4. Relancer `npm run critique-cv` seulement apres un increment editorial significatif.

## Questions ouvertes

- Titre final : garder `Architecte Solution Software & AI Engineer` ou passer a une formulation plus prudente ?
- Quels chiffres exacts peut-on utiliser sur BNP/Sense/Jasmine sans inventer : nombre d'APIs, volumes, latence, batchs, services, apps migrees ?
- Les repos GitHub SAIF-IA / Resell Radar / CV Critic sont-ils publics et presentables ?
- Certifications : garder le plan prive ; ne pas afficher les certifications planifiees dans le CV public.

## Commandes utiles

```bash
npm run lint
npm run build
npm run critique-cv
```

## Fichiers importants

- `src/lib/data.ts`
- `src/lib/chatbot-knowledge.ts`
- `src/lib/system-prompt.ts`
- `src/app/cv/page.tsx`
- `src/components/Projects.tsx`
- `agents/cv-critic/run.mjs`
- `agents/cv-critic/context.md`
- `agents/cv-critic/working-notes.md`
