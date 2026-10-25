import { rulerText } from '../lib/ediPositions';

export default function EdiPreview({ edi }: { edi: string }) {
  const lines = edi ? edi.split('\n').filter(Boolean) : [];
  if (!lines.length) {
    return <div className="kn-edi" aria-label="EDI preview"><pre>Enter a valid query to see the EDI.</pre></div>;
  }
  return (
    <div className="kn-edi" tabIndex={0} aria-label="EDI preview">
      <pre>
        <span className="kn-ruler">{`${rulerText(1)}\n`}</span>
        {lines.map((line) => `[${line}]`).join('\n')}
      </pre>
    </div>
  );
}
