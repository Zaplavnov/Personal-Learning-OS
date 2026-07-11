import {
  Bot,
  CalendarDays,
  FileText,
  Folder,
  Home,
  Network,
  type LucideIcon,
} from "lucide-react";

export type NavigationItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const navigation: NavigationItem[] = [
  { href: "/today", label: "Сегодня", icon: Home },
  { href: "/spaces", label: "Пространства", icon: Folder },
  { href: "/graph", label: "Карта знаний", icon: Network },
  { href: "/materials", label: "Материалы", icon: FileText },
  { href: "/calendar", label: "Календарь", icon: CalendarDays },
  { href: "/tutor", label: "AI-наставник", icon: Bot },
];
