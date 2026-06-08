import Link from "next/link";
import { LaunchButton } from "@/components/LaunchButton";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center gap-16 px-6 py-24 sm:px-10">
      <div className="space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)]/60 px-3 py-1 text-xs uppercase tracking-[0.2em] text-[var(--muted)] backdrop-blur">
          <span className="size-1.5 rounded-full bg-[var(--accent)] shadow-[0_0_8px_var(--accent-glow)]" />
          Live multi-agent visualisation
        </div>
        <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
          Watch three agents think{" "}
          <span className="bg-gradient-to-r from-[var(--accent)] via-[#7af6ff] to-[#ff7ad6] bg-clip-text text-transparent">
            in real time.
          </span>
        </h1>
        <p className="max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
          CV Critic Agent runs a CrewAI pipeline that critiques a software architect&apos;s
          portfolio from three angles. This page streams every lifecycle event over
          Server-Sent Events and animates the dependency graph as the work flows.
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <LaunchButton />
        <Link
          href="/access-request"
          className="inline-flex h-12 items-center justify-center rounded-full border border-[var(--border)] px-6 text-sm font-medium text-[var(--foreground)] transition hover:border-[var(--accent)]/60 hover:bg-[var(--surface)]"
        >
          Request real-run access →
        </Link>
        <Link
          href="https://github.com/Sayfouche/cv-critic-agent"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-12 items-center justify-center rounded-full border border-[var(--border)] px-6 text-sm font-medium text-[var(--foreground)] transition hover:border-[var(--accent)]/60 hover:bg-[var(--surface)]"
        >
          Source on GitHub
        </Link>
      </div>

      <p className="text-xs text-[var(--muted)]">
        Mock runs are instant and free — they use canned fixtures. Real runs hit the
        LLM provider and are manually approved (one or two days).
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            title: "Global Critic",
            desc: "Reads the public portfolio surface — homepage, chatbot, system prompt, tools.",
          },
          {
            title: "Printable CV Critic",
            desc: "Audits the downloadable PDF for A4 readability and ATS friendliness.",
          },
          {
            title: "Strategy Agent",
            desc: "Synthesises both critiques into a prioritised P0 / P1 / P2 action plan.",
          },
        ].map((c) => (
          <div
            key={c.title}
            className="rounded-2xl border border-[var(--border)] bg-[var(--surface)]/60 p-5 backdrop-blur"
          >
            <h2 className="text-sm font-medium tracking-wide text-[var(--foreground)]">
              {c.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{c.desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
