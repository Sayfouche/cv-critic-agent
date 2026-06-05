from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


GLOBAL_SOURCES = [
    "sources/data.ts",
    "sources/chatbot-knowledge.ts",
    "sources/system-prompt.ts",
    "sources/tools.ts",
    "sources/cv-page.tsx",
    "sources/saif-ia-technical-sheet.md",
]

CV_SOURCES = [
    "sources/data.ts",
    "sources/cv-page.tsx",
    "sources/saif-ia-technical-sheet.md",
]


@dataclass(frozen=True)
class ReportSpec:
    slug: str
    title: str
    source_files: tuple[str, ...]
    prompt: str


REPORT_SPECS = [
    ReportSpec(
        slug="global",
        title="Rapport critique global",
        source_files=tuple(GLOBAL_SOURCES),
        prompt="""Analyse tout le dispositif CV/portfolio/chatbot.

Format attendu :
# Rapport critique global

## Verdict court
Donne une note /10 et 4-6 lignes directes.

## Risques de perception
Liste les risques de comprehension cote recruteur, client final, hiring manager, architecte IA.

## Credibilite du positionnement AI Engineer
Dis ce qui est solide, ce qui est fragile, ce qui manque comme preuve.

## Architecture / Solution Architect
Evalue si le CV prouve vraiment architecture, leadership technique, cloud, microservices, delivery.

## ATS et mots-cles
Liste les mots-cles forts presents, les mots-cles manquants, et ceux qui sont trop repetes.

## Points a couper ou condenser
Indique les passages trop longs, trop vagues ou trop techniques pour le CV public.

## Opportunites tactiques pour SAIF-IA
Donne des angles que le chatbot peut utiliser selon recruteur finance, tech, IA, direction.

## Actions prioritaires
Donne 5 a 8 actions concretes, ordonnees, avec impact attendu.""",
    ),
    ReportSpec(
        slug="printable-cv",
        title="Rapport critique CV imprimable",
        source_files=tuple(CV_SOURCES),
        prompt="""Analyse uniquement le CV imprimable / telechargeable expose par la route /cv.

Tu dois le juger comme un recruteur qui ouvre un PDF ou imprime la page. Ignore les details riches reserves au chatbot sauf s'ils montrent un manque dans le CV imprimable.

Format attendu :
# Rapport critique CV imprimable

## Verdict court
Donne une note /10 et 4-6 lignes directes sur le CV telechargeable.

## Lisibilite PDF
Evalue densite, hierarchie, longueur, sections, lisibilite A4, surcharge technique.

## Message en 10 secondes
Dis ce qu'un recruteur retient immediatement, et ce qui reste flou.

## Credibilite du titre
Evalue si "Architecte Solution Software & AI Engineer" est prouve dans le CV imprimable.

## Preuves et manques
Liste les preuves visibles, les preuves manquantes, et les endroits ou il faut ajouter des chiffres ou specs.

## Risques ATS
Analyse mots-cles, titres, repetition, compatibilite ATS et lisibilite machine.

## Coupes et reformulations prioritaires
Propose les elements a couper, condenser ou reformuler dans le CV imprimable.

## Actions prioritaires
Donne 5 a 8 actions concretes pour ameliorer uniquement le CV telechargeable.""",
    ),
]


def read_source_files(root: Path, relative_paths: list[str] | tuple[str, ...]) -> str:
    chunks: list[str] = []
    for relative_path in relative_paths:
        absolute_path = root / relative_path
        if absolute_path.exists():
            content = absolute_path.read_text(encoding="utf-8")
            chunks.append(f"\n\n--- FILE: {relative_path} ---\n{content}")
        else:
            chunks.append(f"\n\n--- FILE: {relative_path} (NOT FOUND - skipped) ---\n")
    return "".join(chunks)


def read_context(root: Path) -> str:
    context_file = root / "context.md"
    if context_file.exists():
        return context_file.read_text(encoding="utf-8")
    return "Aucun contexte specifique fourni."
