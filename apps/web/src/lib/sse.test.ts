import { createSseParser } from "@pdna/api-client";
import { describe, expect, it } from "vitest";

describe("createSseParser", () => {
  it("parses events split across chunks", () => {
    const parse = createSseParser();
    expect(parse('event: start\ndata: {"conversation_id":"c1"}\n\nevent: del')).toEqual([
      { event: "start", data: { conversation_id: "c1" } },
    ]);
    expect(parse('ta\ndata: {"text":"Hi "}\n\n')).toEqual([{ event: "delta", data: { text: "Hi " } }]);
    expect(parse('event: delta\r\ndata: {"text":"there"}\r\n\r\n')).toEqual([{ event: "delta", data: { text: "there" } }]);
  });

  it("skips malformed events", () => {
    const parse = createSseParser();
    expect(parse("event: delta\ndata: {not json\n\nevent: retract\ndata: {}\n\n")).toEqual([
      { event: "retract", data: {} },
    ]);
  });
});
