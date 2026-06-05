from __future__ import annotations

from pathlib import Path
import os

from cv_critic_agent.llm import DEFAULT_ANTHROPIC_MODEL, DEFAULT_MISTRAL_MODEL, MockLLM
from cv_critic_agent.paths import project_root
from cv_critic_agent.prompts import build_critic_prompt, build_strategy_prompt
from cv_critic_agent.reports import create_run_dir, write_report, write_summary
from cv_critic_agent.sources import REPORT_SPECS


class CVCriticCrew:
    """CrewAI-native project class.

    This mirrors the shape produced by `crewai create crew`: a class owns agent
    and task construction, while `main.py` provides the CLI. CrewAI imports stay
    inside `crew()` so unit tests and mock runs do not require network keys.
    """

    def __init__(self, root: Path | None = None, mock: bool = False) -> None:
        self.root = root or project_root()
        self.mock = mock

    def crew(self):
        try:
            from crewai import Agent, Crew, LLM, Process, Task
        except ImportError as exc:
            raise RuntimeError("Install crewai or run the lightweight CLI with --mock.") from exc

        if self.mock:
            return None

        provider = os.getenv("CV_CRITIC_PROVIDER", "mistral").strip().lower()
        default_model = DEFAULT_ANTHROPIC_MODEL if provider == "anthropic" else DEFAULT_MISTRAL_MODEL
        model = os.getenv("CV_CRITIC_MODEL", default_model)
        crew_model = f"{provider}/{model}" if "/" not in model else model
        llm = LLM(model=crew_model, temperature=0.2, max_tokens=5000)
        global_critic = Agent(
            role="External Portfolio Critic",
            goal="Audit the public CV, portfolio and chatbot for credibility and perception risks.",
            backstory="Senior tech recruiter and architecture hiring reviewer.",
            llm=llm,
        )
        cv_critic = Agent(
            role="Printable CV and ATS Specialist",
            goal="Audit the downloadable CV for A4 readability, ATS parsing and title credibility.",
            backstory="ATS consultant for senior IT and AI-transition profiles.",
            llm=llm,
        )
        strategy = Agent(
            role="CV Strategy Synthesizer",
            goal="Turn independent critiques into a P0/P1/P2 action plan.",
            backstory="Career architect specialising in senior backend-to-AI transitions.",
            llm=llm,
        )

        task_global = Task(
            description=build_critic_prompt(REPORT_SPECS[0], self.root),
            expected_output="Markdown report: # Rapport critique global",
            agent=global_critic,
        )
        task_cv = Task(
            description=build_critic_prompt(REPORT_SPECS[1], self.root),
            expected_output="Markdown report: # Rapport critique CV imprimable",
            agent=cv_critic,
        )
        task_strategy = Task(
            description="Synthesize the two previous task outputs using context.md.",
            expected_output="Markdown report: # Strategie CV",
            agent=strategy,
            context=[task_global, task_cv],
        )
        return Crew(
            agents=[global_critic, cv_critic, strategy],
            tasks=[task_global, task_cv, task_strategy],
            process=Process.sequential,
            verbose=True,
        )

    def kickoff(self) -> Path:
        if self.mock:
            from cv_critic_agent.workflow import run_shared_workflow

            return run_shared_workflow(self.root, MockLLM())

        crew = self.crew()
        result = crew.kickoff()
        outputs = result.tasks_output
        global_content = outputs[0].raw if len(outputs) > 0 else result.raw
        printable_content = outputs[1].raw if len(outputs) > 1 else ""
        strategy_content = outputs[2].raw if len(outputs) > 2 else result.raw

        run_dir = create_run_dir(self.root)
        generated = []
        path = write_report(self.root, run_dir, "global", global_content)
        generated.append({"title": "Rapport critique global", "path": str(path)})
        path = write_report(self.root, run_dir, "printable-cv", printable_content)
        generated.append({"title": "Rapport critique CV imprimable", "path": str(path)})
        path = write_report(self.root, run_dir, "strategy", strategy_content)
        generated.append({"title": "Rapport strategie et plan d'action", "path": str(path)})
        write_summary(self.root, run_dir, generated)
        return run_dir
