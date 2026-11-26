import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CoachText } from "./coach-text";

describe("CoachText", () => {
  it("renders light markdown without interpreting HTML", () => {
    const html = renderToStaticMarkup(
      <CoachText text={"**From your results**\nOpenness 72.5\n\n- one _idea_\n- <script>alert(1)</script>"} />,
    );
    expect(html).toContain("<strong>From your results</strong><br/>Openness 72.5");
    expect(html).toContain("<li>one <em>idea</em></li>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
  });

  it("links only known-safe sites", () => {
    const html = renderToStaticMarkup(<CoachText text="Visit findahelpline.com or evil.example.com" />);
    expect(html).toContain('href="https://findahelpline.com"');
    expect(html).not.toContain("evil.example.com\"");
  });
});
