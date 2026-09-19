import DOMPurify from 'dompurify';
import { Marked } from 'marked';

const plainMarkdown = new Marked();
export function renderCard(source: string): string {
  return DOMPurify.sanitize(`<section class="markdown-card">${plainMarkdown.parse(source) as string}</section>`);
}
const markdown = new Marked({ renderer: {
  code(token) {
    if (token.lang?.trim() !== 'card') return false;
    return renderCard(token.text);
  },
} });
export function renderMarkdown(source: string): string {
  return DOMPurify.sanitize(markdown.parse(source) as string);
}
export function renderEditorCards(element: HTMLElement) {
  element.querySelectorAll('pre > code.language-card').forEach(code => {
    const preview = code.parentElement;
    if (!preview) return;
    const html = renderCard(code.textContent || '');
    preview.classList.add('markdown-card-preview');
    preview.innerHTML = html;
  });
}
