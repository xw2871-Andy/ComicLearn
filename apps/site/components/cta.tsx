import Link from "next/link";
import { Github, MessageCircle } from "lucide-react";
import { site } from "@/lib/site";

export function CTA() {
  return (
    <section className="section">
      <div className="mx-auto max-w-4xl rounded-paper border border-rule bg-white p-10 text-center shadow-paper md:p-14">
        <p className="page-no">§ 99 · One more thing</p>
        <h2 className="mt-4 font-serif text-h1">
          Try ComicTeach with your next lesson.
        </h2>
        <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
          Self-host the agent in 60 seconds, or jump into the Discord and we'll
          help you generate your first comic today.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link
            href={site.links.github}
            target="_blank"
            rel="noreferrer"
            className="btn-primary"
          >
            <Github className="h-4 w-4" />
            Get the source
          </Link>
          <Link
            href={site.links.discord}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
          >
            <MessageCircle className="h-4 w-4" />
            Join the Discord
          </Link>
        </div>
      </div>
    </section>
  );
}
