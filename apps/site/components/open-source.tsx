import Link from "next/link";
import { Github, GitFork, Star, MessageCircle, Terminal } from "lucide-react";
import { site } from "@/lib/site";

export function OpenSource() {
  return (
    <section id="open-source" className="bg-ink text-paper">
      <div className="section">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          {/* ---------- Copy ---------- */}
          <div>
            <span className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-paper/60">
              <span className="h-px w-8 bg-paper/30" />
              Open source
            </span>
            <h2 className="mt-4 font-serif text-h1 text-paper">
              Use the hosted studio. Fork the agent when you need more.
            </h2>
            <p className="mt-5 max-w-prose text-lead text-paper/75">
              ComicLearn's public studio is the fastest path for teachers and
              learners. The GitHub repo is there for developers: every prompt,
              QA rubric, and panel renderer is visible, editable, and ready for PRs.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href={site.links.github}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-md bg-paper px-5 py-3 text-sm font-medium text-ink transition hover:bg-cream"
              >
                <Github className="h-4 w-4" />
                View on GitHub
              </Link>
              <Link
                href={site.links.github + "#quickstart"}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-md border border-paper/20 px-5 py-3 text-sm font-medium text-paper transition hover:bg-paper/10"
              >
                <Terminal className="h-4 w-4" />
                Developer quickstart
              </Link>
            </div>
          </div>

          {/* ---------- Repo card ---------- */}
          <div className="rounded-paper border border-paper/15 bg-paper/[0.04] p-6 font-mono text-sm shadow-paper">
            <div className="flex items-center justify-between text-xs text-paper/60">
              <span className="inline-flex items-center gap-2">
                <Github className="h-3.5 w-3.5" />
                xw2871-Andy / ComicLearn
              </span>
              <span className="rounded-full border border-paper/20 px-2 py-0.5 uppercase tracking-wide">
                MIT
              </span>
            </div>

            <div className="mt-5 space-y-1.5 text-[0.78rem] leading-relaxed text-paper/80">
              <RepoLine label="$ git clone" value="https://github.com/xw2871-Andy/ComicLearn.git" />
              <RepoLine label="$ cd"        value="ComicLearn" />
              <RepoLine label="$ pip install" value='-e ".[web]"' />
              <RepoLine label="$ python"   value="run_web.py  # → http://127.0.0.1:8000" />
            </div>

            <div className="mt-6 grid grid-cols-3 gap-3 border-t border-paper/15 pt-5 text-center">
              <RepoStat icon={Star}          n="0" l="Stars" />
              <RepoStat icon={GitFork}       n="0" l="Forks" />
              <RepoStat icon={MessageCircle} n="0" l="Discord" />
            </div>
            <p className="mt-4 text-center text-[0.7rem] uppercase tracking-[0.18em] text-paper/40">
              Day-1 numbers · Help us flip them
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function RepoLine({ label, value }: { label: string; value: string }) {
  return (
    <p>
      <span className="text-indigo-300">{label}</span>{" "}
      <span className="text-paper/95">{value}</span>
    </p>
  );
}

function RepoStat({ icon: Icon, n, l }: { icon: React.ComponentType<{ className?: string }>; n: string; l: string }) {
  return (
    <div>
      <div className="flex items-center justify-center gap-1.5 text-paper">
        <Icon className="h-3.5 w-3.5 text-paper/70" />
        <span className="font-sans text-lg font-semibold">{n}</span>
      </div>
      <p className="mt-1 text-[0.65rem] uppercase tracking-[0.18em] text-paper/50">{l}</p>
    </div>
  );
}
