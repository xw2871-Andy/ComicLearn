import type { Metadata } from "next";
import Link from "next/link";
import { Github, ExternalLink } from "lucide-react";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Docs",
  description: `Get up and running with ${site.name} in under 5 minutes.`
};

export default function DocsPage() {
  return (
    <article className="container py-20 md:py-28">
      <header className="mx-auto max-w-3xl">
        <p className="page-no">§ Docs · v0.1</p>
        <h1 className="mt-4 font-serif text-display">Quickstart</h1>
        <p className="mt-6 max-w-prose text-lead text-muted">
          ComicTeach runs on your machine, your laptop, or your school's server.
          You need Python 3.10+, an Anthropic API key, and about five minutes.
          Full reference docs live in the repo.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href={site.links.github}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
          >
            <Github className="h-4 w-4" />
            Repository
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      <div className="mx-auto mt-14 max-w-prose space-y-12">
        <Step n="01" title="Clone the repo">
          <Code>{`git clone ${site.links.github}.git
cd ComicTeach`}</Code>
        </Step>

        <Step n="02" title="Create a virtual environment">
          <Code>{`python3 -m venv .venv
source .venv/bin/activate`}</Code>
        </Step>

        <Step n="03" title="Install the agent + web UI">
          <Code>{`pip install -e ".[web]"`}</Code>
          <p className="mt-3 text-sm text-muted">
            This installs the core <code className="font-mono text-ink">curriculum_to_comic</code> package
            plus FastAPI/Uvicorn for the local studio.
          </p>
        </Step>

        <Step n="04" title="Add your API keys">
          <Code>{`cat > .env <<EOF
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...      # optional, only for Gemini backend
IMAGE_BACKEND=svg           # 'svg' (free, local) or 'gemini'
EOF`}</Code>
          <p className="mt-3 text-sm text-muted">
            The SVG backend has no API cost and runs entirely on your machine.
            The Gemini backend produces photoreal manga and bills your Google account.
          </p>
        </Step>

        <Step n="05" title="Launch the studio">
          <Code>{`python run_web.py
# → open http://127.0.0.1:8000`}</Code>
          <p className="mt-3 text-sm text-muted">
            Sign up locally (everything stays on your machine), create a project,
            and hit <strong>Generate</strong>. Your first six-page comic should be
            ready in about 90 seconds.
          </p>
        </Step>
      </div>

      <div className="mx-auto mt-20 max-w-prose rounded-paper border border-rule bg-cream/40 p-6">
        <h2 className="font-serif text-h2">Need help?</h2>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Join the <Link className="font-medium text-indigo-700 underline-offset-2 hover:underline" href={site.links.discord} target="_blank" rel="noreferrer">
            ComicTeach Discord
          </Link> — fastest place to get unstuck, swap prompts, and see what other teachers are generating.
        </p>
      </div>
    </article>
  );
}

function Step({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section>
      <header className="flex items-baseline gap-3">
        <span className="page-no">Step {n}</span>
        <h2 className="font-serif text-h2">{title}</h2>
      </header>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto rounded-paper border border-rule bg-ink p-4 font-mono text-[0.8rem] leading-relaxed text-paper shadow-paper">
      <code>{children}</code>
    </pre>
  );
}
