# CV Critic Agent

Repo autonome pour auditer un CV/portfolio via agents specialises, avec migration depuis une orchestration Node.js custom vers CrewAI.

## Implementations conservees

- `src/cv_critic_agent/` : version officielle CrewAI native, structuree comme un projet `crewai create crew`.
- `scripts/crew_script.py` : script Python de migration intermediaire.
- `legacy-node/run.mjs` : version Node.js legacy archivee pour comparaison technique.

Les trois modes produisent le meme contrat :

```text
reports/<timestamp>/
  global.md
  printable-cv.md
  strategy.md
  summary.md

reports/latest/
  global.md
  printable-cv.md
  strategy.md
  summary.md
```

## Commandes

Depuis le checkout sans installation editable :

```bash
PYTHONPATH=src python -m cv_critic_agent.main --mock
PYTHONPATH=src python scripts/crew_script.py --mock
node legacy-node/run.mjs --mock
```

Apres installation du package, la commande exposee est :

```bash
cv-critic-agent --mock
```

## Fournisseur LLM

Le fournisseur est parametrable par variables d'environnement. Par defaut, le repo utilise Mistral :

```bash
CV_CRITIC_PROVIDER=mistral
CV_CRITIC_MODEL=mistral-medium-latest
MISTRAL_API_KEY=...
```

Anthropic reste disponible pour comparaison :

```bash
CV_CRITIC_PROVIDER=anthropic
CV_CRITIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=...
```

Pour un run reel, copier `.env.example` vers `.env.local` puis executer :

```bash
PYTHONPATH=src python -m cv_critic_agent.main
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

Les tests utilisent un Mock LLM et ne font aucun appel API.

## Positionnement CV

CV Critic Agent — repo Python CrewAI autonome pour auditer un CV/portfolio via agents specialises, avec migration depuis une orchestration Node.js custom, comparaison de 3 architectures, tests de non-regression, rapports versionnes et synthese strategique.
