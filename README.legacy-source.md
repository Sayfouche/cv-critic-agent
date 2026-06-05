# CV Critic Agent

Workflow interne pour auditer le positionnement CV/portfolio et produire un plan d'amelioration.

## Separation des roles

### Critic reports

Les rapports critiques ne lisent pas `context.md`.

Objectif : simuler un regard externe, comme un recruteur ou hiring manager qui ne connait que le CV, le site et le chatbot.

- `global.md` : critique du dispositif CV / portfolio / SAIF-IA.
- `printable-cv.md` : critique du CV imprimable / telechargeable.

### Strategy report

Le rapport strategie lit `context.md`.

Objectif : transformer les critiques externes en plan d'action realiste, en tenant compte des contraintes internes deja decidees.

- `strategy.md` : synthese, tensions, decisions recommandees, plan priorise.

## Pourquoi cette separation

Le recruteur n'a pas acces au contexte interne. Les critiques doivent donc rester dures et independantes.

Le contexte sert uniquement a eviter que la strategie propose des actions contraires aux decisions deja prises, par exemple :

- ne pas pretendre avoir implemente seul le module RAG Sense ;
- presenter Resell Radar comme veille automatisee d'annonces publiques ;
- separer SAIF-IA Chatbot et CV Critic Agent.

## Commande

```bash
npm run critique-cv
```

Sorties :

```text
agents/cv-critic/reports/latest/
  global.md
  printable-cv.md
  strategy.md
  summary.md
```
