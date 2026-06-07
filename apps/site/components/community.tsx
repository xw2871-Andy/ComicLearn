import Link from "next/link";
import { MessageCircle, Github, ArrowRight } from "lucide-react";
import { site } from "@/lib/site";

export function Community() {
  return (
    <section id="community" className="bg-cream/50">
      <div className="section">
        <div className="mx-auto grid max-w-6xl items-center gap-12 md:grid-cols-2">
          <div>
            <span className="eyebrow">Community</span>
            <h2 className="mt-4 font-serif text-h1">Build it with us.</h2>
            <p className="mt-5 max-w-prose text-lead text-muted">
              ComicTeach is being built in the open by teachers, students, and
              engineers who think learning should feel less like a textbook and
              more like a Saturday morning cartoon. Drop into Discord, file an
              issue, or send a pull request.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href={site.links.discord}
                target="_blank"
                rel="noreferrer"
                className="btn-primary"
              >
                <MessageCircle className="h-4 w-4" />
                Join the Discord
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href={site.links.github + "/issues/new"}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary"
              >
                <Github className="h-4 w-4" />
                Open an issue
              </Link>
            </div>
          </div>

          <div className="grid gap-4">
            <ChannelRow tag="#welcome" desc="Say hi · share what you teach" />
            <ChannelRow tag="#show-and-tell" desc="Post the comics you generated" />
            <ChannelRow tag="#feature-requests" desc="What should ComicTeach do next?" />
            <ChannelRow tag="#help" desc="Stuck on setup? We'll get you running." />
          </div>
        </div>
      </div>
    </section>
  );
}

function ChannelRow({ tag, desc }: { tag: string; desc: string }) {
  return (
    <div className="flex items-center justify-between rounded-paper border border-rule bg-white px-5 py-4 shadow-chip">
      <div>
        <p className="font-mono text-sm font-medium text-indigo-700">{tag}</p>
        <p className="mt-1 text-sm text-muted">{desc}</p>
      </div>
      <MessageCircle className="h-4 w-4 text-muted" />
    </div>
  );
}
