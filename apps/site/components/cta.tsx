import Link from "next/link";
import { ArrowRight, Github } from "lucide-react";
import { site } from "@/lib/site";

export function CTA() {
  return (
    <section className="section">
      <div className="mx-auto max-w-4xl rounded-paper border border-rule bg-white p-10 text-center shadow-paper md:p-14">
        <p className="page-no">§ 99 · One more thing</p>
        <h2 className="mt-4 font-serif text-h1">
          Try ComicLearn with your next lesson.
        </h2>
        <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
          Open the hosted studio, register with your invite code, and generate
          a comic from a topic, markdown lesson, or textbook PDF.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link
            href={site.links.studio}
            className="btn-primary"
          >
            Open Studio
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href={site.links.github}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
          >
            <Github className="h-4 w-4" />
            Developer source
          </Link>
        </div>
      </div>
    </section>
  );
}
