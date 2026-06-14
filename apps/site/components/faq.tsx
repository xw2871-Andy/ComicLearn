const faqs = [
  {
    q: "Do teachers need their own API keys?",
    a: "No. The hosted studio uses server-side keys, so users register with an invite code and never see provider credentials. Developers can still self-host from GitHub with their own keys."
  },
  {
    q: "What subjects work best?",
    a: "We've tested AP Calculus AB, AP Biology, US History, ESL vocabulary, and 5th-grade fractions. Anything textbook-shaped works. Heavy diagrams (e.g., circuit schematics) are still rough — that's the next frontier."
  },
  {
    q: "How do I get access?",
    a: "Open the hosted studio, create an account, and enter the invite code from the ComicLearn team. Usage is capped so one classroom cannot accidentally drain the API budget."
  },
  {
    q: "How long does generation take?",
    a: "Draft runs can be quick, while high-quality Gemini image runs take longer because pages are generated one by one for consistency. The studio streams each step so you can watch progress."
  },
  {
    q: "Can I use my school's mascot / my own characters?",
    a: "Yes. You can set a custom cast per project and pass reference images for consistency."
  },
  {
    q: "Where does the agent run? Do you see my lessons?",
    a: "The hosted version runs on ComicLearn's backend so provider keys stay hidden. Generated content is stored for your account; do not upload private student data during the research preview."
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
