// Tiny dependency-free PDF writer. Enough for a one-page text document
// (e.g. a demo eviction notice). Helvetica / Latin-1 only.

function esc(s) {
  return String(s).replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
}

// Wrap plain text to a rough character width so long paragraphs don't run off
// the page. Blank strings are kept as spacer lines.
function wrap(text, width = 90) {
  const out = [];
  for (const raw of String(text).split('\n')) {
    if (!raw.trim()) {
      out.push('');
      continue;
    }
    let line = '';
    for (const word of raw.split(/\s+/)) {
      if ((line + ' ' + word).trim().length > width) {
        out.push(line);
        line = word;
      } else {
        line = line ? line + ' ' + word : word;
      }
    }
    if (line) out.push(line);
  }
  return out;
}

// Build a single-page PDF buffer from a block of text.
export function makePdf(text, opts = {}) {
  const fontSize = opts.fontSize || 11;
  const leading = opts.leading || 15;
  const startX = opts.startX || 56;
  const startY = opts.startY || 760;
  const width = opts.width || 92;

  const lines = wrap(text, width);

  let content = `BT\n/F1 ${fontSize} Tf\n${leading} TL\n${startX} ${startY} Td\n`;
  for (const line of lines) content += `(${esc(line)}) Tj T*\n`;
  content += 'ET';

  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${Buffer.byteLength(content, 'latin1')} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];

  let pdf = '%PDF-1.4\n';
  const offsets = [];
  objects.forEach((body, i) => {
    offsets.push(Buffer.byteLength(pdf, 'latin1'));
    pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });

  const xrefStart = Buffer.byteLength(pdf, 'latin1');
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const off of offsets) pdf += `${String(off).padStart(10, '0')} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return Buffer.from(pdf, 'latin1');
}
