import { FileText, Wand2, BookOpen } from "lucide-react";

const steps = [
  {
    icon: FileText,
    title: "Drop in your lesson",
    body:
      "Paste a topic, a markdown outline, or a PDF chapter. The agent ingests it and pulls out objectives, key terms, and worked examples.",
    sub: "Source: topic · markdown · PDF"
  },
  {
    icon: Wand2,
    title: "The agent writes + draws",
    body:
      "Claude writes the lesson plan and storyboard; a visual subagent illustrates six scenes. Every scene is QA-checked for character + concept consistency.",
    sub: "Lesson → Storyboard → Render → QA"
  },
  {
    icon: BookOpen,
    title: "Hand it to your students",
    body:
      "Out comes a six-page comic book PDF — and the open-source repo lets you swap art styles, characters, or even the language entirely.",
    sub: "PDF · PNG · SVG · self-host"
  }
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="section">
      <div className="mx-auto max-w-2xl text-center">
        <span className="eyebrow">How it works</span>
        <h2 className="mt-4 font-serif text-h1">
          Three steps, no design skills required.
        </h2>
        <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
          Under the hood, ComicTeach is a multi-agent pipeline. From your seat,
          it's three boxes and a button.
        </p>
      </div>

      <ol className="mx-auto mt-14 grid max-w-6xl gap-6 md:grid-cols-3">
        {steps.map((s, i) => {
          const Icon = s.icon;
          return (
            <li key={s.title} className="card">
              <div className="mb-5 flex items-center justify-between">
                <span className="grid h-10 w-10 place-items-center rounded-md bg-indigo-50 text-indigo-600">
                  <Icon className="h-5 w-5" />
                </span>
                <span className="page-no">Step {String(i + 1).padStart(2, "0")}</span>
              </div>
              <h3 className="font-serif text-h2">{s.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted">{s.body}</p>
              <p className="mt-5 border-t border-rule pt-3 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted/80">
                {s.sub}
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
