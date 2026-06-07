import { Hero } from "@/components/hero";
import { HowItWorks } from "@/components/how-it-works";
import { Features } from "@/components/features";
import { Showcase } from "@/components/showcase";
import { OpenSource } from "@/components/open-source";
import { UseCases } from "@/components/use-cases";
import { Community } from "@/components/community";
import { Faq } from "@/components/faq";
import { CTA } from "@/components/cta";
import { SectionDivider } from "@/components/section-divider";

export default function HomePage() {
  return (
    <>
      <Hero />
      <SectionDivider pageNo="01" label="How it works" />
      <HowItWorks />
      <Features />
      <SectionDivider pageNo="03" label="Showcase" />
      <Showcase />
      <OpenSource />
      <UseCases />
      <Community />
      <SectionDivider pageNo="07" label="FAQ" />
      <Faq />
      <CTA />
    </>
  );
}
