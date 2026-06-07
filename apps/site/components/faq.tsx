const faqs = [
  {
    q: "Is ComicTeach really free?",
    a: "Yes — the prototype is MIT licensed. You bring your own API keys (Anthropic for the lesson agent, optionally Gemini for the art) and pay only the underlying model providers. A hosted tier can come later for teachers who would rather not manage keys."
  },
  {
    q: "What subjects work best?",
    a: "We've tested AP Calculus AB, AP Biology, US History, ESL vocabulary, and 5th-grade fractions. Anything textbook-shaped works. Heavy diagrams (e.g., circuit schematics) are still rough — that's the next frontier."
  },
  {
    q: "Will it work without an OpenAI / Google account?",
    a: "You need an Anthropic API key for the lesson + storyboard agent. For art, the default SVG backend runs entirely on your machine with no external API. Add a Gemini key if you want photoreal manga."
  },
  {
    q: "How long does generation take?",
    a: "About 90 seconds end-to-end with the SVG backend on a laptop. Gemini takes 2–3 minutes depending on quota and queue. The agent streams progress so you watch each step happen."
  },
  {
    q: "Can I use my school's mascot / my own characters?",
    a: "Yes. You can set a custom cast per project and pass reference images for consistency."
  },
  {
    q: "Where does the agent run? Do you see my lessons?",
    a: "The agent runs on your machine, your laptop, your school's server — wherever you self-host. We have no servers and never see your prompts."
  }
];

export function Faq() {
  return (
    <section id="faq" className="section">
      <div className="mx-auto max-w-2xl text-center">
        <span className="eyebrow">FAQ</span>
        <h2 className="mt-4 font-serif text-h1">Questions teachers actually ask.</h2>
      </div>

      <dl className="mx-auto mt-12 max-w-3xl divide-y divide-rule rounded-paper border border-rule bg-white shadow-paper">
        {faqs.map((f) => (
          <details key={f.q} className="group px-6 py-5">
            <summary className="flex cursor-pointer list-none items-start justify-between gap-6">
              <dt className="font-serif text-lg font-semibold text-ink">{f.q}</dt>
              <span
                aria-hidden
                className="mt-2 grid h-6 w-6 shrink-0 place-items-center rounded-full border border-rule text-xs text-muted transition group-open:rotate-45"
              >
                +
              </span>
            </summary>
            <dd className="mt-3 max-w-prose text-sm leading-relaxed text-muted">{f.a}</dd>
          </details>
        ))}
      </dl>
    </section>
  );
}
