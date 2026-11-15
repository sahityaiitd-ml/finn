import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("styles/tokens.css", "utf8");

describe("design tokens", () => {
  it.each([
    ["--canvas", "#f4efe8"],
    ["--sage-600", "#5e7361"],
    ["--terra", "#b5473d"],
    ["--amber", "#8a5f07"],
  ])("defines %s", (name, value) => {
    expect(css).toContain(`${name}: ${value}`);
  });
});
