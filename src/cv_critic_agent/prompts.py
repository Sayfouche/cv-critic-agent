from __future__ import annotations

from datetime import date
from pathlib import Path

from cv_critic_agent.sources import ReportSpec, read_context, read_source_files


def build_critic_prompt(spec: ReportSpec, root: Path, run_date: date | None = None) -> str:
    current_date = (run_date or date.today()).isoformat()
    sources = read_source_files(root, spec.source_files)

    return f"""Tu es CV Critic Agent, un reviewer interne exigeant pour le portfolio de Saifallah Mansour.

Date du run : {current_date}. Toute date anterieure ou egale a cette date peut etre consideree comme passee ou courante.

Objectif du CV :
- Positionnement cible : Architecte Solution Software + AI Engineer applique.
- Experience affichee : 15+ ans.
- Ne pas maquiller les anciennes missions pro en missions IA si elles ne l'etaient pas.
- Valoriser le socle architecture/backend/cloud/data critique comme base credible pour industrialiser l'IA.
- Le chatbot public SAIF-IA doit qualifier puis convertir, mais ton role a toi est critique interne, pas commercial.

{spec.prompt}

Contraintes :
- Sois franc, meme dur, mais utile.
- Ne propose pas d'inventer des chiffres.
- Signale explicitement les endroits ou il faut demander plus de details a Saifallah.
- Ne reecris pas tout le CV ; concentre-toi sur le diagnostic et les actions.

{sources}"""


def build_strategy_prompt(root: Path, reports: dict[str, str]) -> str:
    return f"""Tu es CV Strategy Agent, un agent de synthese strategique.

Tu ne critiques pas directement le CV depuis les sources. Tu lis :
1. Le contexte utilisateur du run
2. Le rapport critique global
3. Le rapport critique du CV imprimable

Ton objectif : transformer les critiques en plan d'action priorise, coherent et implementable.

Format attendu :
# Strategie CV

## Synthese executive
Resume en 5-8 lignes ce qu'il faut faire maintenant.

## Contradictions ou tensions
Liste les tensions entre les rapports.

## Decisions recommandees
Donne les decisions concretes a prendre, avec recommandation claire.

## Plan d'action priorise
Liste P0, P1, P2 avec actions cocheables Markdown. Pour chaque action : impact attendu, effort, risque.

## Questions a poser a Saifallah
Liste uniquement les questions qui peuvent debloquer une amelioration concrete du CV.

## Definition du prochain increment
Propose un seul prochain increment implementable et testable.

Contraintes :
- Ne propose pas de tout refaire.
- Ne demande pas d'inventer des chiffres.
- Si une preuve manque, propose soit de demander l'information, soit de reformuler plus prudemment.
- Sois oriente execution.

--- CONTEXTE UTILISATEUR ---
{read_context(root)}

--- RAPPORT GLOBAL ---
{reports["global"]}

--- RAPPORT CV IMPRIMABLE ---
{reports["printable-cv"]}"""
