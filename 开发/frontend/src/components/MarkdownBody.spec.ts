import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import MarkdownBody from "./MarkdownBody.vue";

describe("MarkdownBody", () => {
  it("renders markdown and removes scripts", () => {
    const wrapper = mount(MarkdownBody, {
      props: { source: "# 标题\n\n<script>alert(1)</script>正文" },
    });
    expect(wrapper.find("h1").text()).toBe("标题");
    expect(wrapper.html()).not.toContain("<script>");
  });
});


describe("Markdown cards", () => {
  it("renders fenced cards and leaves regular code blocks unchanged", () => {
    const wrapper = mount(MarkdownBody, { props: { source: '```card\n## 提示\n\n- **检查结果**\n```\n\n```js\nconst value = 1;\n```' } });
    expect(wrapper.find('.markdown-card h2').text()).toBe('提示');
    expect(wrapper.find('.markdown-card li strong').text()).toBe('检查结果');
    expect(wrapper.find('code.language-js').text()).toContain('const value');
  });
  it("sanitizes card HTML and links", () => {
    const wrapper = mount(MarkdownBody, { props: { source: '```card\n<img src=x onerror=alert(1)>\n<script>alert(1)</script>\n[bad](javascript:alert(1))\n```' } });
    expect(wrapper.find('.markdown-card').exists()).toBe(true);
    expect(wrapper.html()).not.toMatch(/onerror|<script|href="javascript:/);
  });
});
