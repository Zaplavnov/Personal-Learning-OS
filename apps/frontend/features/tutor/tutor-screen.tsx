"use client";

import { ArrowRight, Link2, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { PageHead } from "@/components/ui/page-head";
import { tutorSuggestions } from "@/lib/mock-data";

export function TutorScreen() {
  const [sent, setSent] = useState(false);
  return <>
    <PageHead eyebrow="Знает твои материалы и историю обучения" title="AI-наставник" />
    <section className="tutor-layout"><div className="chat card"><div className="chat-start"><span className="round-icon blue"><Sparkles /></span><h2>О чём хочешь подумать?</h2><p>Я могу помочь разобраться, но сначала попрошу тебя сформулировать собственную модель.</p><div className="suggestions">{tutorSuggestions.map((suggestion) => <button key={suggestion} type="button">{suggestion}</button>)}</div>{sent && <div className="message"><b>Ты</b><p>Помоги мне проверить понимание собственных векторов.</p></div>}</div><div className="composer"><textarea placeholder="Задай вопрос или вставь своё объяснение…" /><button className="primary" onClick={() => setSent(true)} aria-label="Отправить" type="button"><ArrowRight /></button></div></div><aside className="tutor-context"><section className="card"><h3><Link2 />Контекст диалога</h3><p>Линейная алгебра</p><span>4 концепции</span><span>3 заметки</span><span>2 прошлые ошибки</span></section><section className="card tutor-rule"><ShieldCheck /><h3>AI помогает думать</h3><p>Ответ наставника не считается доказательством твоего знания. Сначала — собственная попытка.</p></section></aside></section>
  </>;
}
