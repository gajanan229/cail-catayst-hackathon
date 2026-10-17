import { describe, expect, it } from "vitest";
import { mergeSnapshot } from "./snapshot";
describe("HTTP snapshot versus realtime continuity", () => {
  const key = (item: { id: string; status: string }) => item.id;
  it("refreshes state missed during disconnection", () => {
    expect(
      mergeSnapshot(
        [{ id: "a", status: "waiting" }],
        [{ id: "a", status: "done" }],
        { a: 4 },
        10,
        key,
        () => true,
      ),
    ).toEqual([{ id: "a", status: "done" }]);
  });
  it("preserves an update received while the HTTP request was in flight", () => {
    expect(
      mergeSnapshot(
        [{ id: "a", status: "done" }],
        [{ id: "a", status: "waiting" }],
        { a: 12 },
        10,
        key,
        () => true,
      ),
    ).toEqual([{ id: "a", status: "done" }]);
  });
  it("keeps removal tombstones and retains unrelated threads", () => {
    expect(
      mergeSnapshot(
        [{ id: "other", status: "done" }],
        [{ id: "a", status: "waiting" }],
        { a: 12 },
        10,
        key,
        (item) => item.id !== "other",
      ),
    ).toEqual([{ id: "other", status: "done" }]);
  });
});
