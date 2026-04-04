import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="hidden w-64 border-r border-slate-200 bg-white p-4 lg:block">
      <nav className="space-y-2 text-sm">
        <Link href="/dashboard" className="block rounded-md px-3 py-2 hover:bg-slate-100">
          Dashboard
        </Link>
        <Link href="/conditions/nf1" className="block rounded-md px-3 py-2 hover:bg-slate-100">
          NF1
        </Link>
      </nav>
    </aside>
  );
}
