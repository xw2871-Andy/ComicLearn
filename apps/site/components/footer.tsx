import Link from "next/link";
import { Github, MessageCircle, Mail } from "lucide-react";
import { site } from "@/lib/site";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-rule bg-cream/40">
      <div className="container py-14">
        <div className="grid gap-10 md:grid-cols-4">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 font-serif text-lg font-semibold">
              <span aria-hidden className="grid h-7 w-7 place-items-center rounded-md bg-ink text-[0.65rem] font-bold tracking-wider text-paper">
                CL
              </span>
              {site.name}
            </div>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">
              Open-source AI learning studio that turns any lesson into a six-page comic.
              Built for teachers who want their students to actually finish the reading.
            </p>
          </div>

          <FooterCol title="Product">
            <FooterLink href={site.links.studio}>Open Studio</FooterLink>
            <FooterLink href="/#how-it-works">How it works</FooterLink>
            <FooterLink href="/#features">Features</FooterLink>
            <FooterLink href="/#showcase">Showcase</FooterLink>
            <FooterLink href="/docs">Docs</FooterLink>
          </FooterCol>

          <FooterCol title="Community">
            <FooterLink href={site.links.github} external>
              <Github className="mr-1.5 inline h-3.5 w-3.5" /> GitHub
            </FooterLink>
            <FooterLink href={site.links.discord} external>
              <MessageCircle className="mr-1.5 inline h-3.5 w-3.5" /> Discord
            </FooterLink>
            <FooterLink href={`mailto:${site.links.email}`} external>
              <Mail className="mr-1.5 inline h-3.5 w-3.5" /> {site.links.email}
            </FooterLink>
            <FooterLink href="/about">About the founder</FooterLink>
          </FooterCol>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-rule pt-6 text-xs text-muted md:flex-row md:items-center">
          <p>© {year} {site.name}. Released under the MIT license.</p>
          <p>
            Built with care in NYC ·{" "}
            <Link href={site.links.github} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
              Read the source
            </Link>
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="mb-3 font-sans text-xs font-semibold uppercase tracking-[0.18em] text-ink">
        {title}
      </h4>
      <ul className="space-y-2">{children}</ul>
    </div>
  );
}

function FooterLink({
  href,
  children,
  external = false
}: {
  href: string;
  children: React.ReactNode;
  external?: boolean;
}) {
  return (
    <li>
      <Link
        href={href}
        target={external ? "_blank" : undefined}
        rel={external ? "noreferrer" : undefined}
        className="text-sm text-muted transition hover:text-ink"
      >
        {children}
      </Link>
    </li>
  );
}
