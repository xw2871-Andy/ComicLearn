import type { Metadata } from "next";
import Link from "next/link";
import { Github, Mail, MessageCircle } from "lucide-react";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description: `Why ${site.name} exists, and who's building it.`
};

export default function AboutPage() {
  return (
    <article className="container py-20 md:py-28">
      <header className="mx-auto max-w-3xl">
        <p className="page-no">§ 00 · About</p>
        <h1 className="mt-4 font-serif text-display">
          We're building the textbook a kid would <span className="ink-underline">choose</span>.
        </h1>
        <p className="mt-6 max-w-prose text-lead text-muted">
          Most students don't fail because the material is too hard. They fail
          because they never start. ComicLearn is a small bet that if a lesson
          looks like the comic on the ride home, it will get read.
        </p>
      </header>

      {/* Founder card */}
      <section className="mx-auto mt-16 max-w-4xl">
        <div className="grid gap-8 rounded-paper border border-rule bg-white p-8 shadow-paper md:grid-cols-[180px_1fr] md:items-start md:p-10">
          <div className="relative aspect-square w-full max-w-[180px] overflow-hidden rounded-paper border border-rule bg-cream">
            {/* Replace public/founder.svg with a headshot when ready. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={site.author.photo}
              alt={site.author.name}
              className="h-full w-full object-cover"
            />
          </div>

          <div>
            <p className="page-no">Founder</p>
            <h2 className="mt-1 font-serif text-h2">{site.author.name}</h2>
            <p className="mt-1 text-sm text-muted">
              {site.author.school} · {site.author.program}
            </p>

            <p className="mt-5 max-w-prose text-base leading-relaxed text-ink">
              {site.author.bio}
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              <Link
                href={site.links.github}
                target="_blank"
                rel="noreferrer"
                className="chip hover:border-ink/30 hover:text-ink"
              >
                <Github className="h-3.5 w-3.5" /> GitHub
              </Link>
              <Link
                href={site.links.discord}
                target="_blank"
                rel="noreferrer"
                className="chip hover:border-ink/30 hover:text-ink"
              >
                <MessageCircle className="h-3.5 w-3.5" /> Discord
              </Link>
              <Link
                href={`mailto:${site.links.email}`}
                className="chip hover:border-ink/30 hover:text-ink"
              >
                <Mail className="h-3.5 w-3.5" /> Email
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Story */}
      <section className="mx-auto mt-20 max-w-prose space-y-6 text-base leading-relaxed text-ink">
        <h2 className="font-serif text-h2">The story</h2>
        <p>
          The first version of {site.name} grew out of a classroom prototype:
          take an AP Calculus chapter, hand it to an AI lesson agent, and ask
          for a six-page comic explaining limits.
        </p>
        <p>
          What came back was rough, but the kids in the test classroom didn't
          care. They read it. Then they argued about whether a character in
          panel four had jumped over the discontinuity. That argument is what we're
          building for.
        </p>
        <p>
          Today {site.name} is a multi-agent pipeline — ingest, lesson plan,
          storyboard, render, QA — that turns any lesson into a finished comic
          in about 90 seconds. It's open source because we want every teacher
          to be able to run it, fork it, and make it their own.
        </p>
      </section>

      <section className="mx-auto mt-20 max-w-prose">
        <h2 className="font-serif text-h2">What we believe</h2>
        <ul className="mt-6 space-y-4 text-base leading-relaxed text-ink">
          <Belief n="01">
            Form is pedagogy. A six-page comic teaches differently than a
            thirty-page PDF — not worse, often better.
          </Belief>
          <Belief n="02">
            Open source is the only ethical AI tool for classrooms. Teachers
            should be able to read every prompt that touches their students.
          </Belief>
          <Belief n="03">
            Good edtech is invisible. The agent should disappear; the student
            should remember the character, not the model.
          </Belief>
        </ul>
      </section>
    </article>
  );
}

function Belief({ n, children }: { n: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-4">
      <span className="page-no shrink-0 pt-1">§ {n}</span>
      <span>{children}</span>
    </li>
  );
}
