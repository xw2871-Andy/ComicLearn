/** Section divider — dotted rule + a "page number" tab on the left. */
export function SectionDivider({ pageNo, label }: { pageNo: string; label: string }) {
  return (
    <div className="container">
      <div className="flex items-center gap-4">
        <span className="page-no whitespace-nowrap">§ {pageNo} · {label}</span>
        <div className="rule-dotted flex-1" />
      </div>
    </div>
  );
}
