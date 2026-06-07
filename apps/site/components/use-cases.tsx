import { GraduationCap, BookOpenCheck, School, Sparkles } from "lucide-react";

const cases = [
  {
    icon: GraduationCap,
    title: "AP teachers",
    quote:
      "Replace the 35-page PDF reading with six pages your students will actually do on the train.",
    detail: "Calculus, Bio, Physics, US History — all covered."
  },
  {
    icon: School,
    title: "Middle-school humanities",
    quote:
      "Turn a primary source — a Frederick Douglass speech, a Roman census — into a graphic novel for tomorrow's class.",
    detail: "Reading-level slider keeps vocabulary on grade."
  },
  {
    icon: BookOpenCheck,
    title: "ESL / multi-language",
    quote:
      "Generate the same lesson in English, Spanish, and Mandarin from one prompt.",
    detail: "Manga form makes new vocab stick."
  },
  {
    icon: Sparkles,
    title: "Homeschool + tutoring",
    quote:
      "Custom lesson, custom character — your kid as the protagonist of their own chemistry textbook.",
    detail: "Free with your own API key."
  }
];

export function UseCases() {
  return (
    <section id="use-cases" className="section">
      <div className="mx-auto max-w-2xl text-center">
        <span className="eyebrow">Who it's for</span>
        <h2 className="mt-4 font-serif text-h1">From AP Calc to 7th-grade history.</h2>
        <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
          ComicTeach isn't tied to one subject. If a textbook can be written,
          it can be drawn.
        </p>
      </div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-5 md:grid-cols-2">
        {cases.map((c) => {
          const Icon = c.icon;
          return (
            <article key={c.title} className="card flex flex-col">
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-md bg-indigo-50 text-indigo-600">
                  <Icon className="h-4 w-4" />
                </span>
                <h3 className="font-serif text-lg font-semibold">{c.title}</h3>
              </div>
              <blockquote className="mt-4 border-l-2 border-accent pl-4 font-serif text-lg leading-snug text-ink">
                &ldquo;{c.quote}&rdquo;
              </blockquote>
              <p className="mt-4 text-sm text-muted">{c.detail}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
