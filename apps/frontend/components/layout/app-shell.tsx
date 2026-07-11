"use client";

import { BrainCircuit, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { navigation } from "@/lib/navigation";
import { BackendStatus } from "./backend-status";
import { ThemeToggle } from "./theme-toggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <Link className="brand" href="/today" onClick={() => setOpen(false)}>
          <span className="brand-mark"><BrainCircuit /></span>
          <span>Personal Learning OS</span>
        </Link>
        <nav aria-label="Основная навигация">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={pathname === href || pathname.startsWith(`${href}/`) ? "active" : ""}
              onClick={() => setOpen(false)}
            >
              <Icon />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">
          <BackendStatus />
          <div className="sync"><span className="online" /> Obsidian синхронизирован</div>
          <div className="profile">
            <div className="avatar">Д</div>
            <div><b>Дмитрий</b><span>Личное пространство</span></div>
            <ThemeToggle />
          </div>
        </div>
      </aside>
      <button
        className="mobile-menu icon-button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Закрыть меню" : "Открыть меню"}
        type="button"
      >
        {open ? <X /> : <Menu />}
      </button>
      <main className="main">{children}</main>
    </div>
  );
}
