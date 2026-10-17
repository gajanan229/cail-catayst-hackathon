import { beforeEach, describe, expect, it } from "vitest";
import { fixture, mockRequest } from "./service";
import { useConsole } from "@/realtime/store";
import type { Schema } from "@/api/types";

describe("rehearsal approval boundaries", () => {
  beforeEach(async () => {
    await mockRequest("/users");
    useConsole.setState({
      readOnly: false,
      actor: "u_priya",
      sim: fixture("rest/GET_sim_state"),
      users: fixture<Schema<"UsersResponse">>("rest/GET_users").users,
      approvals: [],
      terminal: [],
    });
  });
  it("previews the exact action and rejects a static count beyond the ceiling", async () => {
    const result = (await mockRequest("/commands/preview", {
      catalog_id: "pathcom.alter_numstatic",
      params: { server_class: "ATM-AUTH", n: 33 },
      actor: "u_priya",
    })) as Schema<"CommandPreviewResponse">;
    expect(result.rendered).toBe(
      "PATHCOM $PM1; ALTER SERVER ATM-AUTH, NUMSTATIC 33",
    );
    expect(result.valid).toBe(false);
    expect(result.errors.join(" ")).toContain("PATHWAY 2049");
    expect(useConsole.getState().terminal).toHaveLength(0);
  });
  it("read-only disables changes while preserving read-only checks", async () => {
    useConsole.setState({ readOnly: true });
    const action = (await mockRequest("/commands/preview", {
      catalog_id: "tacl.suspend_process",
      params: { process: "$STMT1" },
      actor: "u_priya",
    })) as Schema<"CommandPreviewResponse">;
    const check = (await mockRequest("/commands/preview", {
      catalog_id: "tmfcom.status_audittrail",
      params: {},
      actor: "u_priya",
    })) as Schema<"CommandPreviewResponse">;
    expect(action.rendered).toBe("SUSPEND $STMT1");
    expect(action.policy?.effect).toBe("deny");
    expect(check.policy?.effect).toBe("require_approval");
  });
  it("one persona cannot supply both approvals", async () => {
    const approval = fixture<{ payload: Schema<"Approval"> }>(
      "ws/approval.upsert.partial",
    ).payload;
    useConsole.setState({ approvals: [approval] });
    await expect(
      mockRequest(`/approvals/${approval.id}/decide`, {
        decision: "approve",
        actor: "u_priya",
      }),
    ).rejects.toThrow("different eligible persona");
    expect(useConsole.getState().terminal).toHaveLength(0);
  });
});
