"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { redeemMagicLink } from "@/lib/api";
import { storeAdminSession } from "@/lib/admin-session";

export function AdminSessionRedeem({ token }: { token: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { session_token } = await redeemMagicLink(token);
        if (cancelled) return;
        storeAdminSession(session_token);
        router.replace("/admin/requests");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  if (error) {
    return (
      <p className="rounded-md border border-red-500/40 bg-red-500/5 px-3 py-3 text-sm text-red-300">
        Could not redeem this link: {error}. Request a fresh one from{" "}
        <a href="/admin/login" className="underline">/admin/login</a>.
      </p>
    );
  }
  return <p className="text-sm text-[var(--muted)]">Hang on…</p>;
}
