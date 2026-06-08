"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createAccessRequest } from "@/lib/api";
import { TurnstileWidget } from "./TurnstileWidget";

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";

export function AccessRequestForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [motive, setMotive] = useState("");
  const [website, setWebsite] = useState("");
  const [turnstileToken, setTurnstileToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const captchaConfigured = TURNSTILE_SITE_KEY.length > 0;
  const canSubmit =
    name.trim() &&
    email.trim() &&
    motive.trim() &&
    (!captchaConfigured || turnstileToken) &&
    !busy;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      const { id } = await createAccessRequest({
        name: name.trim(),
        company: company.trim(),
        email: email.trim(),
        motive: motive.trim(),
        website,
        turnstileToken: captchaConfigured ? turnstileToken : undefined,
      });
      router.push(`/access-request/${id}/status`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <Field label="Name *" htmlFor="ar-name">
        <input
          id="ar-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={120}
          className={inputClasses}
          autoComplete="name"
        />
      </Field>

      <Field label="Company or context" htmlFor="ar-company">
        <input
          id="ar-company"
          type="text"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          maxLength={200}
          className={inputClasses}
          autoComplete="organization"
          placeholder="ACME · freelance recruiter · student, etc."
        />
      </Field>

      <Field label="Email *" htmlFor="ar-email">
        <input
          id="ar-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={200}
          className={inputClasses}
          autoComplete="email"
        />
      </Field>

      <Field
        label="Why do you want to run it? *"
        htmlFor="ar-motive"
        hint="One or two lines. Anything you write helps me decide quickly."
      >
        <textarea
          id="ar-motive"
          value={motive}
          onChange={(e) => setMotive(e.target.value)}
          required
          rows={4}
          maxLength={1000}
          className={`${inputClasses} resize-y`}
        />
      </Field>

      {/* honeypot — hidden from humans */}
      <div className="absolute -left-[10000px] h-0 w-0 overflow-hidden" aria-hidden>
        <label htmlFor="ar-website">Website (leave empty)</label>
        <input
          id="ar-website"
          type="text"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      {captchaConfigured ? (
        <TurnstileWidget
          siteKey={TURNSTILE_SITE_KEY}
          onToken={setTurnstileToken}
          onError={() => setTurnstileToken("")}
        />
      ) : (
        <p className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-300">
          Captcha disabled (no <code>NEXT_PUBLIC_TURNSTILE_SITE_KEY</code> set). The
          form will still submit, but production deployments must enable it.
        </p>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex h-12 items-center justify-center rounded-full bg-[var(--accent)] px-6 text-sm font-medium text-white shadow-[0_0_30px_var(--accent-glow)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? "Sending…" : "Send request"}
      </button>

      {error ? (
        <p className="text-xs text-red-400">Could not send request: {error}</p>
      ) : null}
    </form>
  );
}

const inputClasses =
  "w-full rounded-md border border-[var(--border)] bg-[var(--surface)]/60 px-3 py-2 text-sm text-[var(--foreground)] outline-none transition focus:border-[var(--accent)] focus:bg-[var(--surface)]";

function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs text-[var(--muted)]">{hint}</p> : null}
    </div>
  );
}
