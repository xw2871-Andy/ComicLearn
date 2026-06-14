import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Github, ExternalLink } from "lucide-react";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Docs",
  description: `Use ${site.name} as a hosted studio or deploy your own backend.`
};

export default function DocsPage() {
  return (
    <article className="container py-20 md:py-28">
      <header className="mx-auto max-w-3xl">
        <p className="page-no">§ Docs · v0.1</p>
        <h1 className="mt-4 font-serif text-display">Use ComicLearn</h1>
        <p className="mt-6 max-w-prose text-lead text-muted">
          Most teachers should use the hosted studio: keys stay on the server,
          accounts are invite-gated, and generated comics are saved to your
          project history. Developers can still self-host from GitHub.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
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
            Repository
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      <div className="mx-auto mt-14 max-w-prose space-y-12">
        <Step n="01" title="Open the hosted studio">
          <p className="text-sm leading-relaxed text-muted">
            Go to the studio link, create an account, and enter the invite code
            you received. You do not need to clone GitHub or paste API keys.
          </p>
          <Code>{`${site.url}${site.links.studio}`}</Code>
        </Step>

        <Step n="02" title="Create a project">
          <p className="text-sm leading-relaxed text-muted">
            Choose a grade level, cast, and classroom setting. ComicLearn keeps
            each run in your project history so you can download or revise it.
          </p>
        </Step>

        <Step n="03" title="Generate from topic, markdown, or PDF">
          <p className="text-sm leading-relaxed text-muted">
            Pick the input type, choose image quality, and start generation.
            The studio streams lesson planning, storyboard QA, page rendering,
            visual QA, and PDF compilation.
          </p>
        </Step>

        <Step n="04" title="Revise a page">
          <p className="text-sm leading-relaxed text-muted">
            After the PDF is generated, open a page, write specific feedback,
            and redraw only that page. The backend reruns QA and recompiles the PDF.
          </p>
        </Step>

        <Step n="05" title="Developer self-hosting">
          <p className="mt-3 text-sm text-muted">
            Clone the repo only if you want to develop the agent or run your own
            backend with your own provider keys.
          </p>
          <Code>{`git clone ${site.links.github}.git
cd ComicLearn
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[web]"
python run_web.py`}</Code>
        </Step>
      </div>

      <div className="mx-auto mt-20 max-w-prose rounded-paper border border-rule bg-cream/40 p-6">
        <h2 className="font-serif text-h2">Need help?</h2>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          For access, feedback, or a custom school deployment, email{" "}
          <Link className="font-medium text-indigo-700 underline-offset-2 hover:underline" href={`mailto:${site.links.email}`}>
            {site.links.email}
          </Link>.
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
