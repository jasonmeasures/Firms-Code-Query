import { useState } from 'react';
import { cursorInfo, fieldLegend, formatCursor, RECORD_LEN, rulerText } from '../lib/ediPositions';

interface Props {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}

export default function EdiEditor({ value, onChange, placeholder }: Props) {
  const [caret, setCaret] = useState(0);
  const info = cursorInfo(value, caret);
  const over = info.length > RECORD_LEN;

  return (
    <div className="kn-edi kn-edi-shell">
      <pre className="kn-ruler mb-2" aria-hidden="true">{rulerText()}</pre>
      <textarea
        className="kn-edi-editor w-full"
        value={value}
        spellCheck={false}
        placeholder={placeholder}
        aria-label="EDI editor"
        onChange={(event) => {
          onChange(event.target.value);
          setCaret(event.target.selectionStart || 0);
        }}
        onClick={(event) => setCaret(event.currentTarget.selectionStart || 0)}
        onKeyUp={(event) => setCaret(event.currentTarget.selectionStart || 0)}
        onSelect={(event) => setCaret(event.currentTarget.selectionStart || 0)}
      />
      <p className="kn-edi-cursor mt-2 mb-1" style={{ color: over ? '#F58F00' : '#49BFE8' }}>
        {value ? formatCursor(info) : `Position 1 of ${RECORD_LEN}. Click a record to see its field.`}
      </p>
      {info.record && (
        <p className="kn-help mt-0 mb-0" style={{ color: '#94A3B8' }}>{fieldLegend(info.record)}</p>
      )}
    </div>
  );
}
