export default function EdiPreview({ edi }: { edi: string }) {
  const lines = edi ? edi.split('\n').filter(Boolean) : [];
  const ruler = '.'.repeat(9).concat('|').repeat(8);
  const nums = Array.from({ length: 8 }, (_, i) => String((i + 1) * 10).padStart(10)).join('');
  if (!lines.length) {
    return <div className="kn-edi" aria-label="EDI preview"><pre>Enter a valid query to see the EDI.</pre></div>;
  }
  return (
    <div className="kn-edi" tabIndex={0} aria-label="EDI preview">
      <pre>
        <span className="kn-ruler">{` ${nums}\n ${ruler}\n`}</span>
        {lines.map((line) => `[${line}]`).join('\n')}
      </pre>
    </div>
  );
}
