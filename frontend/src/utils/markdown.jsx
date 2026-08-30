/**
 * Lightweight markdown renderer — no external deps.
 * Handles: **bold**, *italic*, # headings, - / 1. lists, --- dividers.
 */

function parseLine(text, key) {
  // Parse inline bold + italic with a single pass
  const parts = []
  const re = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)/g
  let last = 0, m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    if (m[2]) parts.push(<strong key={m.index}><em>{m[2]}</em></strong>)
    else if (m[3]) parts.push(<strong key={m.index}>{m[3]}</strong>)
    else if (m[4]) parts.push(<em key={m.index}>{m[4]}</em>)
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : parts
}

export function Markdown({ text, className = '' }) {
  if (!text) return null

  const lines = text.split('\n')
  const nodes = []
  let listBuffer = []
  let listType = null  // 'ul' | 'ol'

  const flushList = () => {
    if (!listBuffer.length) return
    const Tag = listType === 'ol' ? 'ol' : 'ul'
    nodes.push(
      <Tag key={`list-${nodes.length}`} style={listType === 'ol' ? { listStyleType: 'decimal' } : { listStyleType: 'disc' }}>
        {listBuffer.map((item, i) => (
          <li key={i}>{parseLine(item)}</li>
        ))}
      </Tag>
    )
    listBuffer = []
    listType = null
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]
    const line = raw.trimEnd()

    // Dividers
    if (/^---+$/.test(line.trim())) {
      flushList()
      nodes.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '0.75rem 0' }} />)
      continue
    }

    // Headings
    const h1 = line.match(/^#{1,2}\s+(.+)/)
    if (h1) { flushList(); nodes.push(<h2 key={i}>{parseLine(h1[1])}</h2>); continue }
    const h3 = line.match(/^###\s+(.+)/)
    if (h3) { flushList(); nodes.push(<h3 key={i}>{parseLine(h3[1])}</h3>); continue }

    // Ordered list
    const ol = line.match(/^\d+\.\s+(.+)/)
    if (ol) {
      if (listType !== 'ol') { flushList(); listType = 'ol' }
      listBuffer.push(ol[1])
      continue
    }

    // Unordered list
    const ul = line.match(/^[-*•]\s+(.+)/)
    if (ul) {
      if (listType !== 'ul') { flushList(); listType = 'ul' }
      listBuffer.push(ul[1])
      continue
    }

    // Empty line — paragraph break
    if (!line.trim()) {
      flushList()
      if (nodes.length && nodes[nodes.length - 1]?.type !== 'div') {
        nodes.push(<div key={`gap-${i}`} style={{ height: '0.35em' }} />)
      }
      continue
    }

    // Normal paragraph
    flushList()
    nodes.push(<p key={i}>{parseLine(line)}</p>)
  }

  flushList()

  return <div className={`prose-report ${className}`}>{nodes}</div>
}
