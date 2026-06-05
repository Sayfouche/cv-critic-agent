from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cv_critic_agent.main import run as run_native
from cv_critic_agent.prompts import build_critic_prompt, build_strategy_prompt
from cv_critic_agent.sources import REPORT_SPECS


REPO_ROOT = Path(__file__).resolve().parents[1]


def make_fixture_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="cv-critic-agent-"))
    files = {
        "sources/data.ts": "export const data = 'DATA_SENTINEL';",
        "sources/chatbot-knowledge.ts": "export const knowledge = 'KNOWLEDGE_SENTINEL';",
        "sources/system-prompt.ts": "export const system = 'SYSTEM_SENTINEL';",
        "sources/tools.ts": "export const tools = 'TOOLS_SENTINEL';",
        "sources/cv-page.tsx": "export default function CV(){ return 'CV_PAGE_SENTINEL'; }",
        "sources/saif-ia-technical-sheet.md": "# SHEET_SENTINEL",
        "context.md": "# Context\nSTRATEGY_CONTEXT_SENTINEL",
    }
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


class WorkflowTests(unittest.TestCase):
    def assert_contract(self, root: Path) -> None:
        latest = root / "reports" / "latest"
        for file_name in ["global.md", "printable-cv.md", "strategy.md", "summary.md"]:
            self.assertTrue((latest / file_name).exists(), file_name)

        run_dirs = [p for p in (root / "reports").iterdir() if p.is_dir() and p.name != "latest"]
        self.assertTrue(run_dirs)
        for file_name in ["global.md", "printable-cv.md", "strategy.md", "summary.md"]:
            self.assertTrue((run_dirs[-1] / file_name).exists(), file_name)

    def test_prompts_keep_critics_and_strategy_separate(self) -> None:
        root = make_fixture_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        global_prompt = build_critic_prompt(REPORT_SPECS[0], root)
        printable_prompt = build_critic_prompt(REPORT_SPECS[1], root)
        strategy_prompt = build_strategy_prompt(
            root,
            {
                "global": "# Rapport critique global\nGLOBAL_REPORT_SENTINEL",
                "printable-cv": "# Rapport critique CV imprimable\nPRINTABLE_REPORT_SENTINEL",
            },
        )

        self.assertIn("DATA_SENTINEL", global_prompt)
        self.assertIn("KNOWLEDGE_SENTINEL", global_prompt)
        self.assertNotIn("STRATEGY_CONTEXT_SENTINEL", global_prompt)
        self.assertIn("CV_PAGE_SENTINEL", printable_prompt)
        self.assertNotIn("KNOWLEDGE_SENTINEL", printable_prompt)
        self.assertNotIn("STRATEGY_CONTEXT_SENTINEL", printable_prompt)
        self.assertIn("STRATEGY_CONTEXT_SENTINEL", strategy_prompt)
        self.assertIn("GLOBAL_REPORT_SENTINEL", strategy_prompt)
        self.assertIn("PRINTABLE_REPORT_SENTINEL", strategy_prompt)
        self.assertNotIn("DATA_SENTINEL", strategy_prompt)

    def test_crewai_native_mock_contract(self) -> None:
        root = make_fixture_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        run_native(mock=True, root=root)
        self.assert_contract(root)
        self.assertIn("# Strategie CV", (root / "reports" / "latest" / "strategy.md").read_text(encoding="utf-8"))

    def test_crewai_script_mock_contract(self) -> None:
        root = make_fixture_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "crew_script.py"), "--mock", "--root", str(root)],
            cwd=REPO_ROOT,
            check=True,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        )
        self.assert_contract(root)

    def test_node_legacy_mock_contract(self) -> None:
        root = make_fixture_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        subprocess.run(
            ["node", str(REPO_ROOT / "legacy-node" / "run.mjs"), "--mock", "--root", str(root)],
            cwd=REPO_ROOT,
            check=True,
        )
        self.assert_contract(root)


if __name__ == "__main__":
    unittest.main()
