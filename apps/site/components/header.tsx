import Link from "next/link";
import { Github } from "lucide-react";
import { site } from "@/lib/site";

const nav = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#features",     label: "Features" },
  { href: "/#showcase",     label: "Showcase" },
  { href: "/about",         label: "About" },
  { href: "/docs",          label: "Docs" }
];

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-rule/70 bg-paper/85 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
          <Mark />
          {site.name}
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm text-muted transition hover:text-ink"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href={site.links.github}
            target="_blank"
            rel="noreferrer"
            className="hidden items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs font-medium text-muted shadow-chip transition hover:border-ink/30 hover:text-ink md:inline-flex"
            aria-label="Star on GitHub"
          >
            <Github className="h-4 w-4" />
            Star on GitHub
          </Link>
          <Link href={site.links.discord} target="_blank" rel="noreferrer" className="btn-primary px-4 py-2 text-xs">
            Join Discord
          </Link>
        </div>
      </div>
    </header>
  );
}

function Mark() {
  // Tiny monogram: "CT" inside a paper square — matches the whitepaper vibe.
  return (
    <span aria-hidden className="grid h-7 w-7 place-items-center rounded-md bg-ink text-[0.65rem] font-bold tracking-wider text-paper">
      CT
    </span>
  );
}
