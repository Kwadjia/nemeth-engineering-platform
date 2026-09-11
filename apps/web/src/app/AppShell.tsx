import { NavLink, Outlet } from "react-router-dom";

import { NAV } from "@/app/nav";
import { useHealth } from "@/lib/queries";
import { cn } from "@/lib/utils";

export function AppShell() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 px-6 py-5">
          <Outlet />
        </main>
        <footer className="flex items-center justify-between border-t border-border px-6 py-2 text-2xs text-fg-subtle">
          <span className="tracking-brand">NEMETH · DETROIT</span>
          <span className="font-mono">Engineering Platform v0.1</span>
        </footer>
      </div>
    </div>
  );
}

function Sidebar() {
  return (
    <aside className="brushed sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-border bg-bg-elevated">
      <div className="border-b border-border px-5 pb-4 pt-5">
        <div className="text-base font-semibold tracking-brand text-fg">NEMETH</div>
        <div className="mt-0.5 flex items-center gap-2 text-2xs uppercase tracking-label text-fg-subtle">
          <span className="h-px w-4 bg-border-strong" />
          Engineering Platform
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        {NAV.map((group) => (
          <div key={group.label} className="mb-4">
            <div className="label mb-1 px-2">{group.label}</div>
            <ul className="flex flex-col gap-px">
              {group.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-2.5 rounded px-2 py-1.5 text-sm transition-colors",
                        isActive
                          ? "bg-surface-2 text-fg shadow-raised"
                          : "text-fg-muted hover:bg-surface hover:text-fg",
                      )
                    }
                  >
                    <item.icon className="h-4 w-4 shrink-0 opacity-80" strokeWidth={1.75} />
                    <span className="flex-1 truncate">{item.label}</span>
                    {item.plannedSlice ? (
                      <span
                        className="font-mono text-2xs text-fg-subtle"
                        title={`Planned for slice ${item.plannedSlice}`}
                      >
                        S{item.plannedSlice}
                      </span>
                    ) : null}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}

function TopBar() {
  const health = useHealth();
  const ok = health.data?.status === "ok";
  return (
    <header className="flex h-11 items-center justify-between border-b border-border bg-bg-elevated px-6">
      <div className="text-xs text-fg-subtle">
        Modern American engineering · traditional mechanical watchmaking
      </div>
      <div className="flex items-center gap-4 text-xs">
        <a
          href="/api/v1/docs"
          target="_blank"
          rel="noreferrer"
          className="text-fg-muted hover:text-fg hover:underline"
        >
          API docs
        </a>
        <span className="inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-label text-fg-subtle">
          <span
            className={cn(
              "inline-block h-1.5 w-1.5 rounded-full",
              health.isLoading ? "bg-fg-subtle" : ok ? "bg-ok" : "bg-danger",
            )}
          />
          {health.isLoading ? "API" : ok ? `API ${health.data?.version ?? ""}` : "API offline"}
        </span>
      </div>
    </header>
  );
}
