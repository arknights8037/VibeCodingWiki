export interface WikiTerm {
  slug: string;
  title: string;
  summary: string;
}

// Annotate sanitized HTML text nodes, never Markdown syntax or HTML attributes.
export function annotateWikiTerms(html: string, terms: WikiTerm[]): string {
  const root = document.createElement('div');
  root.innerHTML = html;
  annotateWikiTermElements(root, terms);
  return root.innerHTML;
}

export function annotateWikiTermElements(root: HTMLElement, terms: WikiTerm[]): void {
  for (const button of root.querySelectorAll('button.wiki-term')) {
    button.replaceWith(document.createTextNode(button.textContent || ''));
  }
  const titles = new Map<string, WikiTerm>();
  for (const term of terms) {
    const title = term.title.trim();
    if (title && !titles.has(title.toLowerCase())) titles.set(title.toLowerCase(), term);
  }
  if (!titles.size) return;
  const alternatives = [...titles.keys()].sort((a, b) => b.length - a.length)
    .map(title => title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  // Latin terms must not match inside other words; Chinese terms may adjoin Chinese prose.
  const pattern = new RegExp(`(?<![A-Za-z0-9_])(?:${alternatives.join('|')})(?![A-Za-z0-9_])`, 'gi');
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  while (walker.nextNode()) {
    const node = walker.currentNode as Text;
    if (!node.parentElement?.closest('a, button, code, pre, script, style, textarea, select, svg, math, [contenteditable]')) nodes.push(node);
  }
  for (const node of nodes) {
    const text = node.data;
    const fragment = document.createDocumentFragment();
    let end = 0;
    for (const match of text.matchAll(pattern)) {
      const term = titles.get(match[0].toLowerCase())!;
      fragment.append(text.slice(end, match.index));
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'wiki-term';
      button.dataset.wikiTerm = term.slug;
      button.setAttribute('aria-haspopup', 'dialog');
      button.setAttribute('aria-label', `查看术语释义：${match[0]}`);
      button.textContent = match[0];
      fragment.append(button);
      end = match.index + match[0].length;
    }
    if (end) {
      fragment.append(text.slice(end));
      node.replaceWith(fragment);
    }
  }
}
