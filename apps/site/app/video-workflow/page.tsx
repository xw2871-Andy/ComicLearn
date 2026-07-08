import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BookOpenCheck,
  Captions,
  CheckCircle2,
  Clapperboard,
  Database,
  Film,
  Layers3,
  PackageCheck,
  Play,
  School,
  Sparkles,
  Workflow
} from "lucide-react";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Video Workflow",
  description:
    "ComicLearn's video workflow extends teachable comics into start frames, end frames, shot clips, lesson videos, and social cuts."
};

const pipeline = [
  { icon: School, label: "LessonMeta", detail: "standards, objective, misconception" },
  { icon: BookOpenCheck, label: "ComicPanel", detail: "story beat + learning beat" },
  { icon: Clapperboard, label: "VideoShot", detail: "camera, voiceover, subtitle" },
  { icon: Film, label: "Frames", detail: "start frame + end frame" },
  { icon: Play, label: "Lesson video", detail: "shot clips + social cuts" }
];

const roles = [
  {
    icon: School,
    name: "Curriculum Analyst",
    body: "Extracts grade band, standard, misconception, assessment moment, and the subject-specific thinking mode."
  },
  {
    icon: Sparkles,
    name: "Story Adapter",
    body: "Turns a learning objective into a Last Meridian Academy mission without mixing subjects."
  },
  {
    icon: BookOpenCheck,
    name: "Comic Storyboarder",
    body: "Builds comic pages where every panel carries both a narrative beat and a learning beat."
  },
  {
    icon: Clapperboard,
    name: "Education Video Director",
    body: "Converts high-potential panels into camera language, start/end frames, motion prompts, and voiceover."
  },
  {
    icon: Captions,
    name: "Audio + Subtitle Designer",
    body: "Keeps teacher narration, dialogue, captions, and sound cues short enough for mobile learning."
  },
  {
    icon: Layers3,
    name: "Lesson S-Class Director",
    body: "Combines multiple shots into a coherent hook, concept reveal, application, and exit question."
  }
];

const stages = [
  ["01", "Learning skeleton", "Name the learning function before designing the shot."],
  ["02", "Visual + audio", "Describe what students see, hear, and read on screen."],
  ["03", "Pedagogy control", "Guide attention with diagrams, focus, pacing, and cognitive load."],
  ["04", "Start frame", "Generate a consistent first image from the comic panel and asset library."],
  ["05", "Motion + end frame", "Define movement, camera behavior, final pose, and video prompt."]
];

const qa = [
  "One primary subject per lesson",
  "Every shot has a learning function",
  "Characters use knowledge to decide",
  "Pet/IP prompts but never solves",
  "Frames reuse the same asset library",
  "Video ends with an assessment moment"
];

const outputs = [
  ["Lesson hook", "10-20s", "class opener / social clip"],
  ["Concept reveal", "30-60s", "app micro-lesson"],
  ["Teacher preview", "60-90s", "B2B pilot sales"],
  ["Full comic video", "2-5min", "YouTube / course page"]
];

export default function VideoWorkflowPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-rule bg-white">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(15,23,42,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.18) 1px, transparent 1px)",
            backgroundSize: "28px 28px"
          }}
        />
        <div className="container relative py-16 md:py-24">
          <div className="grid items-center gap-12 lg:grid-cols-[0.92fr_1.08fr]">
            <div>
              <span className="chip">
                <Film className="h-3.5 w-3.5 text-indigo-600" />
                Comic-to-video workflow
              </span>
              <h1 className="mt-6 max-w-3xl font-serif text-4xl font-semibold leading-tight text-ink md:text-5xl">
                Turn a teachable comic into a lesson video.
              </h1>
              <p className="mt-6 max-w-prose text-base leading-8 text-muted md:text-lg">
                ComicLearn now treats each comic page as the master source for
                start frames, end frames, shot clips, voiceover, subtitles, and
                social cuts. API wiring comes later; the production logic starts here.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href={site.links.studio} className="btn-primary">
                  Open Studio
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="#pipeline" className="btn-secondary">
                  View pipeline
                </Link>
              </div>
            </div>

            <HeroBoard />
          </div>
        </div>
      </section>

      <section id="pipeline" className="container py-16 md:py-20">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="page-no">Pipeline</p>
            <h2 className="mt-3 font-serif text-3xl font-semibold">From lesson to moving lesson.</h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            The workflow copies Moyin Creator's core production idea: structured
            knowledge first, reusable assets second, video prompts last.
          </p>
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-5">
          {pipeline.map((item, index) => (
            <PipelineNode key={item.label} item={item} index={index} />
          ))}
        </div>
      </section>

      <section className="border-y border-rule bg-cream/45">
        <div className="container py-16 md:py-20">
          <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
            <div>
              <p className="page-no">AI roles</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold">One job per agent.</h2>
              <p className="mt-4 text-sm leading-7 text-muted">
                A single prompt should not be responsible for curriculum accuracy,
                story, image consistency, camera design, subtitles, and video motion.
                The workflow separates those decisions.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {roles.map((role) => (
                <RoleCard key={role.name} role={role} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="container py-16 md:py-20">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.86fr]">
          <div className="min-w-0">
            <p className="page-no">Five-stage calibration</p>
            <h2 className="mt-3 font-serif text-3xl font-semibold">Video is calibrated after the comic is stable.</h2>
            <div className="mt-8 overflow-hidden rounded-paper border border-rule bg-white shadow-paper">
              {stages.map(([n, title, body]) => (
                <div key={n} className="grid gap-4 border-b border-rule p-5 last:border-b-0 md:grid-cols-[5rem_1fr]">
                  <div className="font-mono text-sm font-medium text-indigo-700">Stage {n}</div>
                  <div>
                    <h3 className="font-sans text-base font-semibold">{title}</h3>
                    <p className="mt-1 text-sm leading-6 text-muted">{body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <aside className="min-w-0 rounded-paper border border-rule bg-ink p-6 text-paper shadow-paper">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-white/10">
                <Database className="h-5 w-5" />
              </span>
              <div>
                <p className="font-mono text-xs uppercase text-paper/60">Core data object</p>
                <h3 className="font-sans text-xl font-semibold text-paper">VideoShot</h3>
              </div>
            </div>
            <pre className="mt-6 max-w-full overflow-x-auto rounded-md border border-white/10 bg-white/5 p-4 text-xs leading-6 text-paper/85">
{`{
  "sourcePanelId": "p03_panel02",
  "learningFunction": "abstraction",
  "shotSize": "MS",
  "duration": 5,
  "visualFocus": "bridge -> beams -> ratio",
  "teacherVoiceover": "A ratio compares two quantities.",
  "subtitle": "30m / 6 beams = 5m each",
  "needsEndFrame": true
}`}
            </pre>
          </aside>
        </div>
      </section>

      <section className="border-y border-rule bg-white">
        <div className="container py-16 md:py-20">
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="page-no">Outputs</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold">One lesson, four video surfaces.</h2>
              <p className="mt-4 text-sm leading-7 text-muted">
                The same comic episode can become a classroom hook, an app
                micro-lesson, a teacher preview, or a complete narrated comic video.
              </p>
            </div>

            <div className="overflow-hidden rounded-paper border border-rule bg-paper">
              <div className="grid grid-cols-[1fr_0.52fr_1.1fr] bg-ink px-4 py-3 text-xs font-semibold uppercase text-paper">
                <span>Product</span>
                <span>Length</span>
                <span>Use</span>
              </div>
              {outputs.map(([product, length, use]) => (
                <div key={product} className="grid grid-cols-[1fr_0.52fr_1.1fr] gap-3 border-b border-rule px-4 py-4 text-sm last:border-b-0">
                  <span className="font-medium text-ink">{product}</span>
                  <span className="font-mono text-xs text-indigo-700">{length}</span>
                  <span className="text-muted">{use}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="container py-16 md:py-20">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <p className="page-no">QA gate</p>
            <h2 className="mt-3 font-serif text-3xl font-semibold">The video must still teach.</h2>
            <p className="mt-4 max-w-prose text-sm leading-7 text-muted">
              The goal is not animated noise. A clip passes only when the
              learning objective, story action, visual consistency, and assessment
              moment survive the move from page to motion.
            </p>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {qa.map((item) => (
                <div key={item} className="flex min-h-14 items-center gap-3 rounded-md border border-rule bg-white px-4 py-3 text-sm shadow-chip">
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-paper border border-rule bg-cream/40 p-6 shadow-paper">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-amber-100 text-amber-700">
                <PackageCheck className="h-5 w-5" />
              </span>
              <h3 className="font-sans text-lg font-semibold">Recommended first demo</h3>
            </div>
            <dl className="mt-6 space-y-4 text-sm">
              <DemoLine label="Subject" value="Grade 6 Math · ratio / unit rate" />
              <DemoLine label="Story" value="Broken bridge on the Hearthline route" />
              <DemoLine label="Comic" value="4 pages from one learning objective" />
              <DemoLine label="Video" value="45-60 second concept reveal" />
              <DemoLine label="Assets" value="2 characters, 1 pet, 1 bridge scene, 4 shot clips" />
            </dl>
          </div>
        </div>
      </section>
    </>
  );
}

function HeroBoard() {
  const pages = [site.showcase.unit1.pages[0], site.showcase.unit1.pages[1], site.showcase.unit1.pages[2]];

  return (
    <div className="mx-auto w-full max-w-2xl rounded-paper border border-rule bg-paper p-4 shadow-paper">
      <div className="grid gap-4 md:grid-cols-[0.84fr_1.16fr]">
        <div className="grid grid-cols-3 gap-2 md:grid-cols-1">
          {pages.map((src, index) => (
            <div key={src} className="relative aspect-[3/4] overflow-hidden rounded-md border border-rule bg-white">
              <Image
                src={src}
                alt={`Comic page source ${index + 1}`}
                fill
                sizes="(min-width: 768px) 11rem, 28vw"
                className="object-cover"
                priority={index === 0}
              />
            </div>
          ))}
        </div>

        <div className="flex min-h-[22rem] flex-col justify-between rounded-md border border-rule bg-white p-5">
          <div>
            <div className="flex items-center justify-between gap-3 border-b border-rule pb-4">
              <div>
                <p className="page-no">Director pack</p>
                <h3 className="mt-1 font-sans text-lg font-semibold">Page to motion</h3>
              </div>
              <Workflow className="h-6 w-6 text-indigo-600" />
            </div>
            <div className="mt-5 space-y-3">
              <VisualRow label="ComicPanel" value="Bridge repair reveal" />
              <VisualRow label="Start frame" value="student measures span" />
              <VisualRow label="End frame" value="ratio diagram appears" />
              <VisualRow label="VideoShot" value="dolly-in, 5s, subtitle on" />
            </div>
          </div>

          <div className="mt-6 rounded-md bg-ink p-4 text-paper">
            <p className="font-mono text-xs uppercase text-paper/60">Motion prompt</p>
            <p className="mt-2 text-sm leading-6 text-paper/90">
              Camera moves from the broken bridge to the beam pile as the ratio
              diagram fades in: 30m / 6 beams = 5m each.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function PipelineNode({ item, index }: { item: { icon: LucideIcon; label: string; detail: string }; index: number }) {
  const Icon = item.icon;
  return (
    <div className="relative rounded-paper border border-rule bg-white p-5 shadow-chip">
      <div className="mb-5 flex items-center justify-between">
        <span className="grid h-10 w-10 place-items-center rounded-md bg-indigo-50 text-indigo-600">
          <Icon className="h-5 w-5" />
        </span>
        <span className="font-mono text-xs text-muted">0{index + 1}</span>
      </div>
      <h3 className="font-sans text-base font-semibold">{item.label}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{item.detail}</p>
    </div>
  );
}

function RoleCard({ role }: { role: { icon: LucideIcon; name: string; body: string } }) {
  const Icon = role.icon;
  return (
    <article className="rounded-paper border border-rule bg-white p-5 shadow-chip">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-md bg-emerald-50 text-emerald-700">
          <Icon className="h-4 w-4" />
        </span>
        <h3 className="font-sans text-base font-semibold">{role.name}</h3>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">{role.body}</p>
    </article>
  );
}

function VisualRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-3 rounded-md bg-cream/50 px-3 py-2 text-sm">
      <span className="font-mono text-xs text-muted">{label}</span>
      <span className="font-medium text-ink">{value}</span>
    </div>
  );
}

function DemoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 border-b border-rule pb-3 last:border-b-0 last:pb-0 sm:grid-cols-[7rem_1fr]">
      <dt className="font-mono text-xs uppercase text-muted">{label}</dt>
      <dd className="leading-6 text-ink">{value}</dd>
    </div>
  );
}
