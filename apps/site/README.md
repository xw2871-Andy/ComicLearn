# ComicLearn — Vercel website

The public-facing website for ComicLearn. It is meant to live on Vercel and
send teachers into the hosted ComicLearn Studio backend.

**Stack:** Next.js 16 (App Router) · Tailwind CSS · TypeScript · deployed on
Vercel.

This folder is the Next.js site inside the main `ComicLearn` repository.

---

## Quickstart

```bash
# 1. install
npm install                # or pnpm install / yarn

# 2. run locally
npm run dev                # → http://localhost:3000

# 3. ship a production build
npm run build && npm start
```

Node 18.17+ is required.

## Project layout

```
comiclearn-site/
├── app/                    # Next.js App Router
│   ├── page.tsx            # Homepage
│   ├── opengraph-image.tsx # Auto-generated OG image
│   ├── robots.ts
│   └── sitemap.ts
├── components/             # Section components (hero, features, etc.)
├── lib/site.ts             # ★ Single source of truth for name + URLs
├── public/showcase/        # Real generated comic pages + demo video
├── tailwind.config.ts      # Whitepaper palette + serif/sans pairing
└── package.json
```

## Brand customization

Almost everything (name, URLs, founder bio, photo path, showcase assets) is
centralized in [`lib/site.ts`](./lib/site.ts). Edit that file once and the
whole site updates.

To change the **photo**, drop `public/founder.jpg`.

To change the **palette**, edit `tailwind.config.ts` (look for `colors.indigo`
and `colors.accent`).

## Deploy

### Vercel

1. Import `https://github.com/xw2871-Andy/ComicLearn` in Vercel.
2. Set **Root Directory** to `apps/site`.
3. Set environment variables:

```bash
NEXT_PUBLIC_SITE_DOMAIN=comiclearn.dpdns.org
NEXT_PUBLIC_SITE_URL=https://comiclearn.dpdns.org
NEXT_PUBLIC_STUDIO_URL=https://your-hosted-studio-url
```

4. Deploy. Every push to `main` will redeploy the site.

### DigitalPlat FreeDomain

Register a free domain from the DigitalPlat dashboard, then add it to the
Vercel project. Vercel will show the DNS record to create, usually:

```text
CNAME  your-subdomain  cname.vercel-dns.com
```

After DNS verifies, update `NEXT_PUBLIC_SITE_DOMAIN` and
`NEXT_PUBLIC_SITE_URL` in Vercel and redeploy.

### Any Node host

```bash
npm run build
npm start          # binds to PORT, defaults to 3000
```

## License

MIT.
