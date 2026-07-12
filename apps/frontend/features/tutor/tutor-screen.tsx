import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { PageHead } from "@/components/ui/page-head";

export function TutorScreen() {
  return <><PageHead eyebrow="Следующий этап" title="AI-наставник" /><section className="card state-card"><span className="round-icon blue"><Sparkles /></span><h2>Наставник пока не подключён</h2><p>На этом этапе система использует только прозрачные rule-based scoring и scheduler. Здесь появится AI-интерфейс после реализации источников, retrieval и правил безопасности.</p><Link className="primary" href="/today">Вернуться к плану <ArrowRight /></Link></section></>;
}
