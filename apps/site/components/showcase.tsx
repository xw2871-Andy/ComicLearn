"use client";

import Image from "next/image";
import { useState } from "react";
import { site } from "@/lib/site";

const tabs = [
  { id: "unit1", title: site.showcase.unit1.title, pages: site.showcase.unit1.pages },
  { id: "unit2", title: site.showcase.unit2.title, pages: site.showcase.unit2.pages }
] as const;

export function Showcase() {
  const [active, setActive] = useState<(typeof tabs)[number]["id"]>("unit1");
  const current = tabs.find((t) => t.id === active)!;

  return (
    <section id="showcase" className="section">
      <div className="mx-auto max-w-3xl text-center">
        <span className="eyebrow">Showcase</span>
        <h2 className="mt-4 font-serif text-h1">A finished lesson, page by page.</h2>
        <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
          These two AP Calculus units were generated end-to-end by ComicTeach.
          Nothing here is hand-drawn or hand-edited.
        </p>
      </div>

      {/* Tabs */}
      <div className="mx-auto mt-10 flex max-w-xl items-center justify-center gap-2 rounded-full border border-rule bg-white p-1 shadow-chip">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={`rounded-full px-4 py-2 text-xs font-medium transition ${
              active === t.id
                ? "bg-ink text-paper"
                : "text-muted hover:text-ink"
            }`}
          >
            {t.title.replace("AP Calculus AB · ", "")}
          </button>
        ))}
      </div>

      {/* Pages */}
      <div className="mx-auto mt-10 grid max-w-6xl grid-cols-2 gap-4 md:grid-cols-3">
        {current.pages.map((src, i) => (
          <figure
            key={src}
            className="group overflow-hidden rounded-paper border border-rule bg-white shadow-paper transition hover:-translate-y-0.5 hover:shadow-lg"
          >
            <div className="relative aspect-[3/4]">
              <Image
                src={src}
                alt={`${current.title} — page ${i + 1}`}
                fill
                sizes="(min-width: 768px) 30vw, 45vw"
                className="object-cover"
              />
            </div>
            <figcaption className="flex items-center justify-between border-t border-rule px-4 py-2.5 text-[0.7rem] uppercase tracking-[0.15em] text-muted">
              <span>Page {i + 1} / 6</span>
              <span>ComicTeach</span>
            </figcaption>
          </figure>
        ))}
      </div>

      {/* Demo video — render only if we have either a hosted MP4 or a YouTube/Vimeo embed URL. */}
      {(site.showcase.demoVideoEmbed || site.showcase.demoVideo) && (
        <div className="mx-auto mt-14 max-w-4xl overflow-hidden rounded-paper border border-rule bg-white shadow-paper">
          <div className="border-b border-rule px-5 py-3 text-xs uppercase tracking-[0.15em] text-muted">
            Generation walkthrough · 1 min
          </div>
          {site.showcase.demoVideoEmbed ? (
            <iframe
              src={site.showcase.demoVideoEmbed}
              title="ComicTeach generation walkthrough"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="aspect-video w-full bg-black"
            />
          ) : (
            <video controls preload="metadata" className="aspect-video w-full bg-black">
              <source src={site.showcase.demoVideo!} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          )}
        </div>
      )}
    </section>
  );
}
