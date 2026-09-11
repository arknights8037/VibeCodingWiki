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
