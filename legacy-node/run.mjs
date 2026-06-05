import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.argv.includes("--root") ? process.argv[process.argv.indexOf("--root") + 1] : process.cwd());
const mock = process.argv.includes("--mock") || process.env.CV_CRITIC_MOCK === "1";

const reportTypes = [
  {
    slug: "global",
    title: "Rapport critique global",
    files: [
      "sources/data.ts",
      "sources/chatbot-knowledge.ts",
      "sources/system-prompt.ts",
      "sources/tools.ts",
      "sources/cv-page.tsx",
      "sources/saif-ia-technical-sheet.md",
    ],
    heading: "# Rapport critique global",
  },
  {
    slug: "printable-cv",
    title: "Rapport critique CV imprimable",
    files: ["sources/data.ts", "sources/cv-page.tsx", "sources/saif-ia-technical-sheet.md"],
    heading: "# Rapport critique CV imprimable",
  },
];

function timestamp() {
  return new Date().toISOString().replaceAll(":", "-").replace(/\.\d{3}Z$/, "Z");
}

function readFiles(files) {
  return files
    .map((file) => {
      const absolute = path.join(root, file);
      const content = existsSync(absolute) ? readFileSync(absolute, "utf8") : "";
      return `\n\n--- FILE: ${file} ---\n${content}`;
    })
    .join("\n");
}

function buildCriticPrompt(type) {
  return `Tu es CV Critic Agent.

${type.heading}

Contraintes : critics independants, pas de context.md.

${readFiles(type.files)}`;
}

function buildStrategyPrompt(reports) {
  const contextPath = path.join(root, "context.md");
  const context = existsSync(contextPath) ? readFileSync(contextPath, "utf8") : "Aucun contexte specifique fourni.";
  return `# Strategie CV

Tu lis context.md et les deux rapports, pas les sources.

--- CONTEXTE UTILISATEUR ---
${context}

--- RAPPORT GLOBAL ---
${reports.global}

--- RAPPORT CV IMPRIMABLE ---
${reports["printable-cv"]}`;
}

async function complete(prompt) {
  if (mock) {
    if (prompt.includes("# Rapport critique global")) return "# Rapport critique global\n\n## Verdict court\nMock global critic output.";
    if (prompt.includes("# Rapport critique CV imprimable")) return "# Rapport critique CV imprimable\n\n## Verdict court\nMock printable CV critic output.";
    return "# Strategie CV\n\n## Synthese executive\nMock strategy output.";
  }

  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const model = process.env.CV_CRITIC_MODEL ?? "claude-haiku-4-5-20251001";
  const message = await client.messages.create({
    model,
    max_tokens: 5000,
    ...(model.includes("claude-opus-4") ? {} : { temperature: 0.2 }),
    messages: [{ role: "user", content: prompt }],
  });
  return message.content.filter((block) => block.type === "text").map((block) => block.text).join("\n\n").trim();
}

function writeReport(runDir, latestDir, slug, content) {
  const text = `${content.trim()}\n`;
  writeFileSync(path.join(runDir, `${slug}.md`), text, "utf8");
  writeFileSync(path.join(latestDir, `${slug}.md`), text, "utf8");
}

async function main() {
  if (!mock && !process.env.ANTHROPIC_API_KEY) {
    throw new Error("ANTHROPIC_API_KEY is required unless --mock is used.");
  }

  const runDir = path.join(root, "reports", timestamp());
  const latestDir = path.join(root, "reports", "latest");
  mkdirSync(runDir, { recursive: true });
  mkdirSync(latestDir, { recursive: true });

  const reports = {};
  const generated = [];
  for (const type of reportTypes) {
    const content = await complete(buildCriticPrompt(type));
    reports[type.slug] = content;
    writeReport(runDir, latestDir, type.slug, content);
    generated.push(`- ${type.title}: ${type.slug}.md`);
  }

  const strategy = await complete(buildStrategyPrompt(reports));
  writeReport(runDir, latestDir, "strategy", strategy);
  generated.push("- Rapport strategie et plan d'action: strategy.md");

  const summary = `# CV Critic Run Summary

Generated at: ${path.basename(runDir)}
Engine: Node.js legacy

## Reports
${generated.join("\n")}
`;
  writeReport(runDir, latestDir, "summary", summary);
  console.log(`[cv-critic-node-legacy] reports written to ${runDir}`);
}

main().catch((error) => {
  console.error("[cv-critic-node-legacy]", error);
  process.exit(1);
});
