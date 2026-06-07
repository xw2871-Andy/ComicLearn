import {
  ShieldCheck,
  Languages,
  Palette,
  Users,
  FileDown,
  GitBranch
} from "lucide-react";

const features = [
  {
    icon: ShieldCheck,
    title: "Concept-faithful by construction",
    body:
      "Every panel is reviewed by a visual QA subagent against the lesson's learning objectives. Failures auto-retry. No hallucinated calculus.",
  },
  {
    icon: Palette,
    title: "Swappable art backends",
    body:
      "Start with the free SVG illustrator. Plug in Gemini Nano Banana 2 for photoreal manga, or wire your own model in ~40 lines.",
  },
  {
    icon: Users,
    title: "Bring your own cast",
    body:
      "Use original classroom characters, a school mascot, or student-created personas. Reference images can keep the cast consistent.",
  },
  {
    icon: Languages,
    title: "Any subject, any grade",
    body:
      "Tested on AP Calculus, AP Bio, US History, and 5th-grade fractions. The lesson agent adapts vocabulary to the reading level you set.",
  },
  {
    icon: FileDown,
    title: "Classroom-ready output",
    body:
      "Six print-ready pages, a teacher key with discussion prompts, and a single-click PDF — drop it in Google Classroom and go.",
  },
  {
    icon: GitBranch,
    title: "Open-source forever",
    body:
      "MIT license. Run it locally, on one classroom machine, or on a school server. No vendor lock-in.",
  }
];

export function Features() {
  return (
    <section id="features" className="bg-cream/50">
      <div className="section">
        <div className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">Features</span>
          <h2 className="mt-4 font-serif text-h1">
            Built for classrooms, not for benchmarks.
          </h2>
          <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
            We've watched too many "AI tutors" generate beautiful nonsense. Every
            choice in ComicTeach is downstream of one question: <em>will a real
            student understand this?</em>
          </p>
        </div>

        <div className="mx-auto mt-14 grid max-w-6xl gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="card">
                <div className="mb-4 grid h-9 w-9 place-items-center rounded-md bg-indigo-50 text-indigo-600">
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="font-serif text-lg font-semibold leading-snug">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{f.body}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
