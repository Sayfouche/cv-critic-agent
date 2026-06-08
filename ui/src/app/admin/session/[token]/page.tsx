import { notFound } from "next/navigation";
import { AdminSessionRedeem } from "@/components/AdminSessionRedeem";

type Params = Promise<{ token: string }>;

export const metadata = {
  title: "Admin · redeeming link — CV Critic Agent",
};

export default async function AdminSessionRedeemPage({ params }: { params: Params }) {
  const { token } = await params;
  if (!token || token.length < 10) notFound();

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-6 py-16 sm:px-10">
      <h1 className="text-2xl font-semibold tracking-tight">Signing you in…</h1>
      <AdminSessionRedeem token={token} />
    </main>
  );
}
