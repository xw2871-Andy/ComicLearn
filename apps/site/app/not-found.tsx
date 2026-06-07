import Link from "next/link";

export default function NotFound() {
  return (
    <section className="container py-32 text-center">
      <p className="page-no">§ 404</p>
      <h1 className="mt-4 font-serif text-display">Page not found.</h1>
      <p className="mx-auto mt-4 max-w-prose text-lead text-muted">
        That page hasn't been drawn yet.
      </p>
      <Link href="/" className="btn-primary mt-8 inline-flex">
        Back to the homepage
      </Link>
    </section>
  );
}
