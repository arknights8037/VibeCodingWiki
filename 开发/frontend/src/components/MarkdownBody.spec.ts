import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import MarkdownBody from "./MarkdownBody.vue";
async function render(source: string) { const wrapper = mount(MarkdownBody, { props: { source } }); await nextTick(); await new Promise(resolve => setTimeout(resolve, 20)); return wrapper; }
describe("MarkdownBody", () => {
  it("omits only a matching opening title and preserves other headings", async () => {
    const wrapper = mount(MarkdownBody, { props: { source: '# **Git**\n\n正文\n\n## 使用建议', titleToOmit: 'Git' } });
    expect(wrapper.find('h1').exists()).toBe(false);
    expect(wrapper.find('h2').text()).toBe('使用建议');
    await wrapper.setProps({ source: '# 另一个标题\n\n正文' });
    expect(wrapper.find('h1').text()).toBe('另一个标题');
  });
  it("renders spaced bold Markdown as strong text", async () => { const wrapper = await render("**  xxx  **"); expect(wrapper.find("strong").text()).toBe("xxx"); });
  it("renders markdown and removes scripts", async () => { const wrapper = await render("# 标题\n\n<script>alert(1)</script>正文"); expect(wrapper.find("h1").text()).toBe("标题"); expect(wrapper.html()).not.toContain("<script>"); });
});
describe("Markdown cards", () => {
  it("renders fenced cards and leaves regular code blocks unchanged", async () => { const wrapper = await render('```card\n## 提示\n\n- **检查结果**\n```\n\n```js\nconst value = 1;\n```'); expect(wrapper.find('.markdown-card h2').text()).toBe('提示'); expect(wrapper.find('.markdown-card li strong').text()).toBe('检查结果'); expect(wrapper.find('code').text()).toContain('const value'); });
  it("sanitizes card HTML and links", async () => { const wrapper = await render('```card\n<img src=x onerror=alert(1)>\n<script>alert(1)</script>\n[bad](javascript:alert(1))\n```'); expect(wrapper.find('.markdown-card').exists()).toBe(true); expect(wrapper.html()).not.toMatch(/onerror|<script|href="javascript:/); });
});
