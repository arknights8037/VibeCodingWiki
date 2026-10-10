import { describe, expect, it } from 'vitest';
import { renderMarkdown } from './markdown';
import { annotateWikiTerms, type WikiTerm } from './wikiTerms';

const terms: WikiTerm[] = ['API', 'API Key', '提示词', 'C++', 'a.b'].map(title => ({ title, slug: title, summary: '释义' }));
function annotate(source: string, index = terms) {
  const element = document.createElement('div');
  element.innerHTML = annotateWikiTerms(renderMarkdown(source), index);
  return element;
}
describe('automatic wiki terms', () => {
  it('prefers long terms, preserves casing, escapes punctuation and respects English boundaries', () => {
    const root = annotate('api key、API、CAPITAL、APIClient，使用提示词和C++，a.b axb');
    expect([...root.querySelectorAll('button')].map(node => node.textContent)).toEqual(['api key', 'API', '提示词', 'C++', 'a.b']);
  });
  it('leaves links, code and attributes untouched while supporting cards and formatting', () => {
    const root = annotate('[API](/wiki/api) `API`\n\n```js\nAPI\n```\n\n**API**\n\n```card\n提示词\n```\n\n<img alt="API" src="/API.png">');
    expect(root.querySelectorAll('button')).toHaveLength(2);
    expect(root.querySelector('a')?.textContent).toBe('API');
    expect(root.querySelectorAll('code button')).toHaveLength(0);
    expect(root.querySelector('img')?.getAttribute('alt')).toBe('API');
  });
  it('recomputes associations after either content or terms change without injecting markup', () => {
    expect(annotate('API', []).querySelector('button')).toBeNull();
    expect(annotate('API').querySelector('button')).not.toBeNull();
    expect(annotate('其他正文').querySelector('button')).toBeNull();
    const root = annotate('API<script>alert(1)</script>', [{ title: 'API', slug: '\"><img src=x onerror=alert(1)>', summary: '' }]);
    expect(root.querySelector('script, img')).toBeNull();
    expect(root.querySelector('button')?.dataset.wikiTerm).toContain('<img');
  });
});
