/**
 * Central place for site-wide constants. Edit these to rebrand or swap
 * GitHub/Discord URLs without hunting through every page.
 */
export const site = {
  name: "ComicTeach",
  domain: "comicteach.com",
  url: "https://comicteach.com",
  tagline: "Turn lessons into teachable comics.",
  description:
    "ComicTeach is an open-source AI learning studio that turns any lesson — from AP Calculus to 7th-grade history — into a six-page comic students will actually finish.",
  author: {
    name: "Xingkai Wang",
    school: "Duke University",
    program: "Economics & Secondary Math Education",
    bio:
      "Hi — I'm Xingkai Wang, a Duke undergrad studying Economics and Secondary Math Education. I'm interested in AI and education, specifically how new technology will transform our current education system, policies, communities of interest, and beyond.",
    photo: "/founder.svg"
  },
  links: {
    github: "https://github.com/xw2871-Andy/ComicTeach",
    discord: "https://discord.gg/sUZPnP7P",
    twitter: "https://twitter.com/comicteach",
    email: "xw2871@nyu.edu"
  },
  // Showcase assets live in public/showcase/.
  showcase: {
    unit1: {
      title: "AP Calculus AB · Unit 1.1 — Limits",
      pages: Array.from({ length: 6 }, (_, i) => `/showcase/unit_1_1/page${i + 1}.png`)
    },
    unit2: {
      title: "AP Calculus AB · Unit 1.2 — Derivatives",
      pages: Array.from({ length: 6 }, (_, i) => `/showcase/unit_1_2/page${i + 1}.png`)
    },
    // The raw demo MP4 is 138MB, which is above Vercel's 100MB per-file limit.
    // Host it on YouTube unlisted / Vimeo / Cloudflare Stream and paste the embed URL
    // here. Set to null to hide the video block entirely.
    demoVideo: null as string | null,
    demoVideoEmbed: null as string | null // e.g. "https://www.youtube.com/embed/abc123"
  }
};

export type SiteConfig = typeof site;
