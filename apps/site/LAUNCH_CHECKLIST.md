# Showcase Launch Checklist

Use this when preparing the public site in `apps/site`.

## Local Review

- [ ] Run `npm install`.
- [ ] Run `npm run dev` and open `http://localhost:3000`.
- [ ] Confirm the hero renders generated comic pages from `public/showcase`.
- [ ] Confirm all navigation links stay on valid homepage sections.
- [ ] Run `npm run build`.

## Content

- [ ] Confirm the GitHub URL points to `https://github.com/xw2871-Andy/ComicLearn`.
- [ ] Replace Discord/Twitter links if they are not active.
- [ ] Add a production demo video URL in `lib/site.ts` if one is available.
- [ ] Add a founder image only if the page design uses it.

## Deploy

- [ ] Create a Vercel project from `apps/site`.
- [ ] Set the build command to `npm run build`.
- [ ] Set the output framework to Next.js.
- [ ] Add the production domain when ready.
