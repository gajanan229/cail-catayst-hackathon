export interface paths {
    "/api/system/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** System Status */
        get: operations["system_status_api_system_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/read-only": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** System Read Only */
        post: operations["system_read_only_api_system_read_only_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Users */
        get: operations["users_api_users_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sim/state": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sim State */
        get: operations["sim_state_api_sim_state_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sim/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sim Start */
        post: operations["sim_start_api_sim_start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sim/inject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sim Inject */
        post: operations["sim_inject_api_sim_inject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sim/clock": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sim Clock */
        post: operations["sim_clock_api_sim_clock_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sim/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sim Reset */
        post: operations["sim_reset_api_sim_reset_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sim/replay": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sim Replay */
        post: operations["sim_replay_api_sim_replay_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/topology": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topology */
        get: operations["topology_api_topology_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Metrics */
        get: operations["metrics_api_metrics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Events */
        get: operations["events_api_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/episodes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Episodes */
        get: operations["episodes_api_episodes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/situations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Situations */
        get: operations["situations_api_situations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/situations/{situation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Situation */
        get: operations["situation_api_situations__situation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/situations/{situation_id}/investigate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Investigate */
        post: operations["investigate_api_situations__situation_id__investigate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/threads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Thread */
        post: operations["create_thread_api_threads_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/threads/{thread_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Thread Detail */
        get: operations["thread_detail_api_threads__thread_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/threads/{thread_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Message */
        post: operations["post_message_api_threads__thread_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/threads/{thread_id}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resume */
        post: operations["resume_api_threads__thread_id__resume_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/approvals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Approvals */
        get: operations["approvals_api_approvals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/approvals/{approval_id}/decide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide */
        post: operations["decide_api_approvals__approval_id__decide_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Catalog */
        get: operations["catalog_api_catalog_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/commands/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview */
        post: operations["preview_api_commands_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/terminal/input": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Terminal Input */
        post: operations["terminal_input_api_terminal_input_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/executions/{exec_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Execution */
        get: operations["execution_api_executions__exec_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/executions/{exec_id}/undo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Undo */
        post: operations["undo_api_executions__exec_id__undo_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incidents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Incidents */
        get: operations["incidents_api_incidents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incidents/{incident_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Incident */
        get: operations["incident_api_incidents__incident_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incidents/{incident_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Timeline */
        get: operations["timeline_api_incidents__incident_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incidents/{incident_id}/postmortem": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Postmortem */
        get: operations["postmortem_api_incidents__incident_id__postmortem_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incidents/{incident_id}/close": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Close Incident */
        post: operations["close_incident_api_incidents__incident_id__close_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incidents/{incident_id}/whatif": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Whatif
         * @description P1: 600 sim-second prediction for candidate actions; use incident_id "none" outside an incident.
         */
        post: operations["whatif_api_incidents__incident_id__whatif_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/kb/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Kb Search */
        get: operations["kb_search_api_kb_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/kb/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Kb Item */
        get: operations["kb_item_api_kb_items__item_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/claims": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Claims */
        get: operations["claims_api_claims_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/claims/{claim_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review Claim */
        post: operations["review_claim_api_claims__claim_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/playbooks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Playbooks */
        get: operations["playbooks_api_playbooks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/playbooks/{playbook_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Playbook */
        get: operations["playbook_api_playbooks__playbook_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ledger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ledger */
        get: operations["ledger_api_ledger_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ledger/{key}/grant": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Ledger Grant */
        post: operations["ledger_grant_api_ledger__key__grant_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ledger/{key}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Ledger Revoke */
        post: operations["ledger_revoke_api_ledger__key__revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/policies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Policies */
        get: operations["policies_api_policies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit */
        get: operations["audit_api_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/audit/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit Verify */
        get: operations["audit_verify_api_audit_verify_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/eval/latest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Eval Latest */
        get: operations["eval_latest_api_eval_latest_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/eval/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Eval Run */
        post: operations["eval_run_api_eval_run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** ActiveFault */
        ActiveFault: {
            /**
             * Fault
             * @enum {string}
             */
            fault: "cpu_halt" | "audit_pressure" | "maxservers_change" | "runaway_batch";
            /** Params */
            params: {
                [key: string]: unknown;
            };
            /** Injected Sim Ts */
            injected_sim_ts: string;
        };
        /** ActorOnly */
        ActorOnly: {
            /** Actor */
            actor: string;
        };
        /** ActorRef */
        ActorRef: {
            /**
             * Type
             * @enum {string}
             */
            type: "user" | "agent" | "system";
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** Approval */
        Approval: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string;
            /** Incident Id */
            incident_id: string | null;
            /** Card Id */
            card_id: string | null;
            /** Step Ids */
            step_ids: string[];
            /**
             * Option Ids
             * @default []
             */
            option_ids: string[];
            /** Rendered */
            rendered: string[];
            /**
             * Tier
             * @enum {string}
             */
            tier: "T0" | "T1" | "T2" | "T3";
            required: components["schemas"]["ApprovalRequired"];
            /**
             * Decisions
             * @default []
             */
            decisions: components["schemas"]["ApprovalDecisionRecord"][];
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "partially_approved" | "approved" | "rejected" | "expired";
            /** Expires Sim Ts */
            expires_sim_ts: string;
            policy: components["schemas"]["PolicyDecision"];
            /**
             * Progress Text
             * @description e.g. '1 of 2: needs Senior or Expert'
             */
            progress_text: string;
        };
        /** ApprovalDecideRequest */
        ApprovalDecideRequest: {
            /**
             * Decision
             * @enum {string}
             */
            decision: "approve" | "edit_approve" | "reject";
            /**
             * Params
             * @description Edited parameters (edit_approve); for multi-step approvals {step_id: params}
             */
            params?: {
                [key: string]: unknown;
            } | null;
            /**
             * Option Ids
             * @description Decision cards: the options ticked by the operator
             */
            option_ids?: string[] | null;
            /** Reason Code */
            reason_code?: ("wrong_command" | "wrong_target" | "unsafe_now" | "not_needed" | "other") | null;
            /** Comment */
            comment?: string | null;
            /** Actor */
            actor: string;
        };
        /** ApprovalDecideResponse */
        ApprovalDecideResponse: {
            approval: components["schemas"]["Approval"];
            /**
             * Resumed
             * @description True when the decision completed the approval and resumed the thread
             */
            resumed: boolean;
        };
        /** ApprovalDecisionRecord */
        ApprovalDecisionRecord: {
            /** Actor */
            actor: string;
            /** Actor Name */
            actor_name: string;
            /**
             * Decision
             * @enum {string}
             */
            decision: "approve" | "edit_approve" | "reject";
            /** At */
            at: string;
            /** Reason Code */
            reason_code?: ("wrong_command" | "wrong_target" | "unsafe_now" | "not_needed" | "other") | null;
            /** Comment */
            comment?: string | null;
            /** Params */
            params?: {
                [key: string]: unknown;
            } | null;
        };
        /** ApprovalRequired */
        ApprovalRequired: {
            /** Count */
            count: number;
            /** Roles */
            roles: ("operator" | "senior" | "expert" | "steward")[];
            /**
             * At Least One Of
             * @default []
             */
            at_least_one_of: ("operator" | "senior" | "expert" | "steward")[];
        };
        /** ApprovalsResponse */
        ApprovalsResponse: {
            /** Approvals */
            approvals: components["schemas"]["Approval"][];
        };
        /** AuditResponse */
        AuditResponse: {
            /** Rows */
            rows: components["schemas"]["AuditRow"][];
        };
        /** AuditRow */
        AuditRow: {
            /** Seq */
            seq: number;
            /** Wall Ts */
            wall_ts: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Actor Type
             * @enum {string}
             */
            actor_type: "user" | "agent" | "system";
            /** Actor Id */
            actor_id: string;
            /** Action */
            action: string;
            /** Target */
            target: string | null;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Policy Rule Ids
             * @default []
             */
            policy_rule_ids: string[];
            /** Model Id */
            model_id?: string | null;
            /** Prompt Hash */
            prompt_hash?: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /** Prev Hash */
            prev_hash: string;
            /** Hash */
            hash: string;
        };
        /** AuditVerify */
        AuditVerify: {
            /** Valid */
            valid: boolean;
            /** Entries */
            entries: number;
            /** Head Hash */
            head_hash: string;
            /** First Bad Seq */
            first_bad_seq?: number | null;
        };
        /** Autonomy */
        Autonomy: {
            /**
             * Level
             * @enum {string}
             */
            level: "L0" | "L1" | "L2" | "L3" | "system";
            /** Key */
            key: string;
            /** Progress */
            progress: string;
            /** Granted By */
            granted_by: string | null;
        };
        /** CatalogEntryPublic */
        CatalogEntryPublic: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Interpreter */
            interpreter: string | null;
            /** Template */
            template: string | null;
            /**
             * Syntax Status
             * @enum {string}
             */
            syntax_status: "simulated" | "verified";
            /**
             * Tier
             * @enum {string}
             */
            tier: "T0" | "T1" | "T2" | "T3";
            /** Tier Rules */
            tier_rules: string;
            /** Params */
            params: components["schemas"]["CatalogParam"][];
            /** Reversible */
            reversible: boolean;
            /** Undo Template */
            undo_template: string | null;
            /** Side Effects */
            side_effects: string;
            /** Risks */
            risks: string;
            /**
             * Internal
             * @description Baton-internal check (baton.*): never typed into the terminal
             */
            internal: boolean;
            /**
             * Blocked
             * @default false
             */
            blocked: boolean;
            /** Escalation */
            escalation?: string | null;
            /**
             * Aliases
             * @default []
             */
            aliases: string[];
            /** Utility */
            utility: string;
        };
        /** CatalogParam */
        CatalogParam: {
            /** Name */
            name: string;
            /**
             * Type
             * @enum {string}
             */
            type: "int" | "str" | "enum" | "process" | "cpu" | "volume" | "server_class";
            /**
             * Required
             * @default true
             */
            required: boolean;
            /** Min */
            min?: number | null;
            /** Max */
            max?: number | null;
            /** Max From */
            max_from?: string | null;
            /** Source */
            source?: string | null;
            /** Choices */
            choices?: string[] | null;
            /** Description */
            description?: string | null;
        };
        /** CatalogResponse */
        CatalogResponse: {
            /** Entries */
            entries: components["schemas"]["CatalogEntryPublic"][];
        };
        /** Citation */
        Citation: {
            /**
             * Id
             * @description Knowledge item ID, e.g. 'opmsg:PATHWAY:1034', 'cmdref:tmfcom.status_audittrail', 'claim:C-001'
             */
            id: string;
            /** Label */
            label: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "hpe_manual" | "command_ref" | "concept" | "claim" | "playbook" | "incident" | "site" | "glossary" | "evidence";
            /** Url */
            url?: string | null;
        };
        /** Claim */
        Claim: {
            /** Id */
            id: string;
            /** Statement */
            statement: string;
            structured: components["schemas"]["ClaimStructured"];
            /** Scope */
            scope: {
                [key: string]: unknown;
            };
            /** Confidence */
            confidence: ("certain" | "likely" | "tentative") | string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending_review" | "verified" | "rejected" | "retired";
            /** Author */
            author: string;
            /** Author Name */
            author_name?: string | null;
            /** Assigned Reviewer */
            assigned_reviewer?: string | null;
            /**
             * Reviews
             * @default []
             */
            reviews: components["schemas"]["ClaimReview"][];
            /**
             * Version
             * @default 1
             */
            version: number;
            provenance: components["schemas"]["ClaimProvenance"];
            /**
             * Synthetic
             * @default true
             */
            synthetic: boolean;
        };
        /** ClaimProvenance */
        ClaimProvenance: {
            /**
             * Source Type
             * @enum {string}
             */
            source_type: "seed" | "incident" | "interview" | "manual";
            /** Source Id */
            source_id: string | null;
        };
        /** ClaimReview */
        ClaimReview: {
            /** User */
            user: string;
            /** User Name */
            user_name?: string | null;
            /**
             * Decision
             * @enum {string}
             */
            decision: "confirm" | "edit_confirm" | "reject";
            /** At */
            at: string;
            /** Reason */
            reason?: string | null;
            /** Edits */
            edits?: {
                [key: string]: unknown;
            } | null;
        };
        /** ClaimReviewBody */
        ClaimReviewBody: {
            /** Claim Id */
            claim_id: string;
            /** Statement */
            statement: string;
            /** Structured */
            structured: {
                [key: string]: unknown;
            };
            /** Scope */
            scope: {
                [key: string]: unknown;
            };
            /** Author */
            author: string;
            /** Assigned Reviewer */
            assigned_reviewer: string | null;
            /** Source */
            source: {
                [key: string]: unknown;
            };
        };
        /** ClaimReviewCard */
        ClaimReviewCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "claim_review";
            body: components["schemas"]["ClaimReviewBody"];
        };
        /** ClaimReviewRequest */
        ClaimReviewRequest: {
            /**
             * Decision
             * @enum {string}
             */
            decision: "confirm" | "edit_confirm" | "reject";
            /**
             * Edits
             * @description Fields to change: statement, structured, scope, confidence
             */
            edits?: {
                [key: string]: unknown;
            } | null;
            /** Reason */
            reason?: string | null;
            /** Actor */
            actor: string;
        };
        /** ClaimStructured */
        ClaimStructured: {
            /** Subject */
            subject: string[];
            /** Condition */
            condition: string;
            /** Assertion */
            assertion: string;
            /** Recommendation */
            recommendation?: {
                [key: string]: unknown;
            } | string | null;
            /** Rationale */
            rationale: string;
        };
        /** ClaimsResponse */
        ClaimsResponse: {
            /** Claims */
            claims: components["schemas"]["Claim"][];
        };
        /** CommandBody */
        CommandBody: {
            /** Step Id */
            step_id: string;
            /** Catalog Id */
            catalog_id: string;
            /** Interpreter */
            interpreter: string | null;
            /** Rendered */
            rendered: string;
            /**
             * Params
             * @default {}
             */
            params: {
                [key: string]: unknown;
            };
            /** Purpose */
            purpose: string;
            /** Why Now */
            why_now?: {
                [key: string]: unknown;
            } | null;
            /** Expected */
            expected?: string | null;
            /** Risks */
            risks: string;
            /**
             * Tier
             * @enum {string}
             */
            tier: "T0" | "T1" | "T2" | "T3";
            /**
             * Internal
             * @description Baton check: not typed into the terminal
             * @default false
             */
            internal: boolean;
            autonomy: components["schemas"]["Autonomy"] | null;
            policy: components["schemas"]["PolicyDecision"];
            undo: components["schemas"]["UndoSpec"] | null;
            /** Approval Id */
            approval_id: string | null;
            /** Approval Progress */
            approval_progress?: string | null;
            /**
             * Approvers
             * @default []
             */
            approvers: string[];
            execution: components["schemas"]["CommandExecution"] | null;
            /**
             * Validation Errors
             * @default []
             */
            validation_errors: string[];
        };
        /** CommandCard */
        CommandCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "command";
            body: components["schemas"]["CommandBody"];
        };
        /** CommandExecution */
        CommandExecution: {
            /** Exec Id */
            exec_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "done" | "failed";
            /** Duration Ms */
            duration_ms: number | null;
            /** Raw Output */
            raw_output: string | null;
            /** Facts */
            facts: {
                [key: string]: unknown;
            } | null;
            /**
             * Facts Table
             * @default []
             */
            facts_table: components["schemas"]["FactsRow"][];
            /** Summary */
            summary?: string | null;
            /** Summary Source */
            summary_source?: string | null;
            /**
             * Approved By
             * @default []
             */
            approved_by: string[];
            /**
             * Auto
             * @default false
             */
            auto: boolean;
        };
        /** CommandPreviewRequest */
        CommandPreviewRequest: {
            /** Catalog Id */
            catalog_id: string;
            /**
             * Params
             * @default {}
             */
            params: {
                [key: string]: unknown;
            };
            /** Actor */
            actor: string;
        };
        /** CommandPreviewResponse */
        CommandPreviewResponse: {
            /** Valid */
            valid: boolean;
            /** Errors */
            errors: string[];
            /** Rendered */
            rendered: string | null;
            /** Tier */
            tier: ("T0" | "T1" | "T2" | "T3") | null;
            policy: components["schemas"]["PolicyDecision"] | null;
            /** Undo */
            undo?: string | null;
        };
        /** DecisionBody */
        DecisionBody: {
            /**
             * Approval Id
             * @description Set once options have been selected and approvals created
             */
            approval_id?: string | null;
            /** Options */
            options: components["schemas"]["DecisionOption"][];
            /**
             * Selected
             * @default []
             */
            selected: string[];
        };
        /** DecisionCard */
        DecisionCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "decision";
            body: components["schemas"]["DecisionBody"];
        };
        /** DecisionOption */
        DecisionOption: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /**
             * Steps
             * @default []
             */
            steps: components["schemas"]["OptionStep"][];
            /** Tier */
            tier?: ("T0" | "T1" | "T2" | "T3") | null;
            /** Required Approvers */
            required_approvers?: number | null;
            recommender?: components["schemas"]["Recommender"] | null;
            /** Expected Effect */
            expected_effect?: string | null;
            /** Risks */
            risks?: string | null;
            /** Prediction */
            prediction?: {
                [key: string]: unknown;
            } | null;
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
            /**
             * Blocked
             * @default false
             */
            blocked: boolean;
            /** Block Reason */
            block_reason?: string | null;
            /** Escalation */
            escalation?: string | null;
            /**
             * Includes
             * @default []
             */
            includes: string[];
            /** Approval Id */
            approval_id?: string | null;
            /**
             * Status
             * @default available
             * @enum {string}
             */
            status: "available" | "selected" | "awaiting_approval" | "partially_approved" | "approved" | "executed" | "rejected" | "blocked";
        };
        /** Episode */
        Episode: {
            /** Id */
            id: string;
            /** Fingerprint */
            fingerprint: string;
            /** Subsystem */
            subsystem: string;
            /** Event Number */
            event_number: number;
            /** Example Text */
            example_text: string;
            /** Component Id */
            component_id: string | null;
            /** Count */
            count: number;
            /** Rate Per Min */
            rate_per_min: number;
            /** First At */
            first_at: string;
            /** Last At */
            last_at: string;
            /** Severity */
            severity: number;
            /** Critical */
            critical: boolean;
            /** Quarantined */
            quarantined: boolean;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "closed";
            manual?: components["schemas"]["ManualRef"] | null;
        };
        /** EpisodesResponse */
        EpisodesResponse: {
            /** Episodes */
            episodes: components["schemas"]["Episode"][];
        };
        /** ErrorDetail */
        ErrorDetail: {
            /**
             * Code
             * @enum {string}
             */
            code: "VALIDATION_FAILED" | "POLICY_DENIED" | "APPROVAL_EXPIRED" | "NOT_FOUND" | "CONFLICT" | "SIM_NOT_RUNNING";
            /** Message */
            message: string;
            /** Detail */
            detail?: {
                [key: string]: unknown;
            } | null;
            /** Correlation Id */
            correlation_id: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorDetail"];
        };
        /** EscalationBody */
        EscalationBody: {
            /** Reason */
            reason: string;
            /** Contact */
            contact: string;
            /** Summary */
            summary: string;
            /**
             * Evidence Pack
             * @default []
             */
            evidence_pack: string[];
        };
        /** EscalationCard */
        EscalationCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "escalation";
            body: components["schemas"]["EscalationBody"];
        };
        /** EvalCaseResult */
        EvalCaseResult: {
            /**
             * Suite
             * @enum {string}
             */
            suite: "commands" | "safety" | "diagnosis" | "retrieval";
            /** Case Id */
            case_id: string;
            /** Passed */
            passed: boolean;
            /** Input */
            input: string;
            /** Expected */
            expected: unknown;
            /** Actual */
            actual: unknown;
            /**
             * Detail
             * @default
             */
            detail: string;
        };
        /** EvalLatestResponse */
        EvalLatestResponse: {
            run: components["schemas"]["EvalRun"] | null;
        };
        /** EvalRun */
        EvalRun: {
            /** Id */
            id: string;
            /** Started At */
            started_at: string;
            /** Ended At */
            ended_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "done" | "failed";
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /**
             * Tiles
             * @default []
             */
            tiles: components["schemas"]["EvalTile"][];
            /**
             * Results
             * @default []
             */
            results: components["schemas"]["EvalCaseResult"][];
        };
        /** EvalRunAccepted */
        EvalRunAccepted: {
            /** Run Id */
            run_id: string;
        };
        /** EvalRunRequest */
        EvalRunRequest: {
            /** Suites */
            suites?: ("commands" | "safety" | "diagnosis" | "retrieval")[] | null;
            /** Actor */
            actor?: string | null;
        };
        /** EvalTile */
        EvalTile: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Value */
            value: number;
            /** Display */
            display: string;
            /** Target */
            target: string;
            /** Passed */
            passed: boolean;
        };
        /** EventsResponse */
        EventsResponse: {
            /** Events */
            events: components["schemas"]["NormalizedEvent"][];
        };
        /** EvidenceBody */
        EvidenceBody: {
            /**
             * Items
             * @description [{id, type: metric|event|episode|output_fact|knowledge|site_fact, label, source, preview}]
             */
            items: {
                [key: string]: unknown;
            }[];
        };
        /** EvidenceCard */
        EvidenceCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "evidence";
            body: components["schemas"]["EvidenceBody"];
        };
        /** EvidenceRef */
        EvidenceRef: {
            /** Evidence Id */
            evidence_id: string;
            /** Label */
            label: string;
        };
        /** Execution */
        Execution: {
            /** Id */
            id: string;
            /** Step Id */
            step_id: string | null;
            /** Catalog Id */
            catalog_id: string;
            /**
             * Params
             * @default {}
             */
            params: {
                [key: string]: unknown;
            };
            /** Rendered */
            rendered: string;
            /** Approved By */
            approved_by: string[];
            /** Auto */
            auto: boolean;
            /** Actor */
            actor: string;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "done" | "failed";
            /** Started At */
            started_at: string;
            /** Ended At */
            ended_at: string | null;
            /** Sim Ts */
            sim_ts: string;
            /** Raw Text */
            raw_text: string | null;
            /** Facts */
            facts: {
                [key: string]: unknown;
            } | null;
            /** Parse Confidence */
            parse_confidence: number | null;
            /** Undo Entry Id */
            undo_entry_id: string | null;
            /** Summary */
            summary?: string | null;
        };
        /** ExpertBody */
        ExpertBody: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "playbook" | "claim";
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Version */
            version: number;
            author: components["schemas"]["PersonRef"];
            /** Verified By */
            verified_by: components["schemas"]["PersonRef"][];
            /** Last Validated */
            last_validated: string | null;
            /** Tip */
            tip: string;
            /**
             * Steps
             * @default []
             */
            steps: string[];
            /**
             * Claim Ids
             * @default []
             */
            claim_ids: string[];
            /**
             * Claims
             * @description [{id, statement, author, verified_by}]
             * @default []
             */
            claims: {
                [key: string]: unknown;
            }[];
            /**
             * Synthetic
             * @default true
             */
            synthetic: boolean;
        };
        /** ExpertCard */
        ExpertCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "expert";
            body: components["schemas"]["ExpertBody"];
        };
        /** FactsRow */
        FactsRow: {
            /** Label */
            label: string;
            /** Value */
            value: string;
        };
        /** HealthComponent */
        HealthComponent: {
            /**
             * Id
             * @description Component ID, e.g. 'cpu:3', 'sc:ATM-AUTH', 'tmf:mat', 'svc:atm'
             */
            id: string;
            /**
             * Type
             * @enum {string}
             */
            type: "cpu" | "server_class" | "tmf" | "service" | "process" | "volume";
            /** Name */
            name: string;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "degraded" | "critical" | "down" | "unknown";
            /**
             * Reasons
             * @default []
             */
            reasons: components["schemas"]["HealthReason"][];
            /**
             * At Risk
             * @default false
             */
            at_risk: boolean;
            /**
             * Metrics
             * @default {}
             */
            metrics: {
                [key: string]: number;
            };
        };
        /** HealthReason */
        HealthReason: {
            /** Rule Id */
            rule_id: string;
            /** Text */
            text: string;
            /** Value */
            value?: number | null;
            /** Threshold */
            threshold?: number | null;
        };
        /** HealthResponse */
        HealthResponse: {
            /** Sim Ts */
            sim_ts: string;
            /**
             * Overall
             * @enum {string}
             */
            overall: "ok" | "degraded" | "critical" | "down" | "unknown";
            /** Components */
            components: components["schemas"]["HealthComponent"][];
            n1: components["schemas"]["N1Status"];
        };
        /** HypothesesBody */
        HypothesesBody: {
            /** Round */
            round: number;
            stop_rule: components["schemas"]["StopRule"];
            /** Hypotheses */
            hypotheses: components["schemas"]["Hypothesis"][];
            /** Narrative */
            narrative?: string | null;
            /** Narrative Source */
            narrative_source?: string | null;
        };
        /** HypothesesCard */
        HypothesesCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "hypotheses";
            body: components["schemas"]["HypothesesBody"];
        };
        /** Hypothesis */
        Hypothesis: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** P */
            p: number;
            /** Delta */
            delta: number;
            /**
             * For
             * @default []
             */
            for: components["schemas"]["EvidenceRef"][];
            /**
             * Against
             * @default []
             */
            against: components["schemas"]["EvidenceRef"][];
            /** Would Change Mind */
            would_change_mind?: string | null;
        };
        /** HypothesisTop */
        HypothesisTop: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** P */
            p: number;
        };
        /** Incident */
        Incident: {
            /** Id */
            id: string;
            /** Display Id */
            display_id: string;
            /** Title */
            title: string;
            /** Severity */
            severity: number;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "mitigating" | "verifying" | "resolved";
            /** Situation Id */
            situation_id: string | null;
            /** Thread Id */
            thread_id: string | null;
            /** Opened At */
            opened_at: string;
            /** Resolved At */
            resolved_at: string | null;
            impact: components["schemas"]["IncidentImpact"];
            /**
             * Hypotheses Top
             * @default []
             */
            hypotheses_top: components["schemas"]["HypothesisTop"][];
            /**
             * Undo Stack
             * @default []
             */
            undo_stack: components["schemas"]["UndoEntry"][];
        };
        /** IncidentDetail */
        IncidentDetail: {
            /** Id */
            id: string;
            /** Display Id */
            display_id: string;
            /** Title */
            title: string;
            /** Severity */
            severity: number;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "mitigating" | "verifying" | "resolved";
            /** Situation Id */
            situation_id: string | null;
            /** Thread Id */
            thread_id: string | null;
            /** Opened At */
            opened_at: string;
            /** Resolved At */
            resolved_at: string | null;
            impact: components["schemas"]["IncidentImpact"];
            /**
             * Hypotheses Top
             * @default []
             */
            hypotheses_top: components["schemas"]["HypothesisTop"][];
            /**
             * Undo Stack
             * @default []
             */
            undo_stack: components["schemas"]["UndoEntry"][];
            /**
             * Hypotheses
             * @default []
             */
            hypotheses: {
                [key: string]: unknown;
            }[];
            /**
             * Options
             * @default []
             */
            options: {
                [key: string]: unknown;
            }[];
            /**
             * Approvals
             * @default []
             */
            approvals: components["schemas"]["Approval"][];
            /**
             * Executions
             * @default []
             */
            executions: components["schemas"]["Execution"][];
            /** Verification */
            verification?: {
                [key: string]: unknown;
            } | null;
            /**
             * Postmortem Ready
             * @default false
             */
            postmortem_ready: boolean;
            /**
             * Cards
             * @default []
             */
            cards: (components["schemas"]["TextCard"] | components["schemas"]["SituationCard"] | components["schemas"]["CommandCard"] | components["schemas"]["PlanCard"] | components["schemas"]["HypothesesCard"] | components["schemas"]["EvidenceCard"] | components["schemas"]["ExpertCard"] | components["schemas"]["DecisionCard"] | components["schemas"]["VerificationCard"] | components["schemas"]["EscalationCard"] | components["schemas"]["PostmortemCard"] | components["schemas"]["ClaimReviewCard"])[];
        };
        /** IncidentImpact */
        IncidentImpact: {
            /** Service */
            service: string | null;
            /** P95 Ms Peak */
            p95_ms_peak: number | null;
            /** Timeout Pct Peak */
            timeout_pct_peak: number | null;
        };
        /** IncidentsResponse */
        IncidentsResponse: {
            /** Incidents */
            incidents: components["schemas"]["Incident"][];
        };
        /** Interrupt */
        Interrupt: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string;
            /** Run Id */
            run_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "approval" | "question";
            /** Approval Id */
            approval_id?: string | null;
            /** Prompt */
            prompt: string;
            /** Raised At */
            raised_at: string;
            /**
             * Resolved
             * @default false
             */
            resolved: boolean;
        };
        /** InvestigateResponse */
        InvestigateResponse: {
            /** Thread Id */
            thread_id: string;
            /** Incident Id */
            incident_id: string;
        };
        /** KbItem */
        KbItem: {
            /** Id */
            id: string;
            /** Doc Type */
            doc_type: string;
            /** Title */
            title: string;
            /** Text */
            text: string;
            /** Header */
            header: string;
            /**
             * Metadata
             * @default {}
             */
            metadata: {
                [key: string]: unknown;
            };
            /** Provenance */
            provenance: string;
            /** Source Url */
            source_url?: string | null;
            /**
             * Synthetic
             * @default false
             */
            synthetic: boolean;
            /**
             * Record
             * @description Full source record (message, claim, playbook, ...)
             * @default {}
             */
            record: {
                [key: string]: unknown;
            };
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
        };
        /** KbResult */
        KbResult: {
            /** Id */
            id: string;
            /**
             * Doc Type
             * @enum {string}
             */
            doc_type: "operator_message" | "command_ref" | "concept" | "claim" | "playbook" | "playbook_step" | "incident" | "glossary" | "site_fact" | "catalog";
            /** Title */
            title: string;
            /** Snippet */
            snippet: string;
            /**
             * Provenance
             * @enum {string}
             */
            provenance: "hpe_manual" | "expert_verified" | "site" | "incident" | "synthetic";
            /** Source Url */
            source_url?: string | null;
            /**
             * Synthetic
             * @default false
             */
            synthetic: boolean;
            scores?: components["schemas"]["KbStageScores"] | null;
        };
        /** KbSearchResponse */
        KbSearchResponse: {
            /** Query */
            query: string;
            /**
             * Expanded Terms
             * @default []
             */
            expanded_terms: string[];
            /**
             * Entities
             * @default []
             */
            entities: string[];
            /** Results */
            results: components["schemas"]["KbResult"][];
        };
        /** KbStageScores */
        KbStageScores: {
            /** Bm25 Rank */
            bm25_rank: number | null;
            /** Vector Rank */
            vector_rank: number | null;
            /** Fused */
            fused: number;
            /** Authority */
            authority: number;
            /** Final */
            final: number;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
        };
        /** LedgerCounters */
        LedgerCounters: {
            /**
             * Approved Unchanged
             * @default 0
             */
            approved_unchanged: number;
            /**
             * Edited
             * @default 0
             */
            edited: number;
            /**
             * Rejected
             * @default 0
             */
            rejected: number;
            /**
             * Executed
             * @default 0
             */
            executed: number;
            /**
             * Verified Ok
             * @default 0
             */
            verified_ok: number;
            /**
             * Verified Fail
             * @default 0
             */
            verified_fail: number;
            /**
             * Undone
             * @default 0
             */
            undone: number;
        };
        /** LedgerEntry */
        LedgerEntry: {
            /**
             * Key
             * @description '{catalog_id}|{param_class}|{role}'
             */
            key: string;
            /** Catalog Id */
            catalog_id: string;
            /** Param Class */
            param_class: string;
            /** Role */
            role: string;
            /**
             * Level
             * @enum {string}
             */
            level: "L0" | "L1" | "L2" | "L3" | "system";
            counters: components["schemas"]["LedgerCounters"];
            /** Distinct Approvers */
            distinct_approvers: number;
            /** Granted By */
            granted_by: string | null;
            /** Granted At */
            granted_at: string | null;
            /** Grant Reason */
            grant_reason: string | null;
            /**
             * Eligible For
             * @description Set when a promotion candidate is open
             */
            eligible_for?: ("L0" | "L1" | "L2" | "L3" | "system") | null;
            /**
             * Recent Rejections
             * @default 0
             */
            recent_rejections: number;
            /** Tier */
            tier?: ("T0" | "T1" | "T2" | "T3") | null;
            /**
             * History
             * @default []
             */
            history: components["schemas"]["LedgerHistoryItem"][];
        };
        /** LedgerGrantRequest */
        LedgerGrantRequest: {
            /**
             * Level
             * @enum {string}
             */
            level: "L0" | "L1" | "L2" | "L3" | "system";
            /** Reason */
            reason: string;
            /** Actor */
            actor: string;
        };
        /** LedgerHistoryItem */
        LedgerHistoryItem: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "seed" | "promotion_candidate" | "grant" | "demotion" | "revocation";
            /** Actor */
            actor: string;
            /** Reason */
            reason: string;
            /** At */
            at: string;
            /** From Level */
            from_level?: ("L0" | "L1" | "L2" | "L3" | "system") | null;
            /** To Level */
            to_level?: ("L0" | "L1" | "L2" | "L3" | "system") | null;
        };
        /** LedgerResponse */
        LedgerResponse: {
            /** Entries */
            entries: components["schemas"]["LedgerEntry"][];
        };
        /** LedgerRevokeRequest */
        LedgerRevokeRequest: {
            /** Reason */
            reason: string;
            /** Actor */
            actor: string;
        };
        /** ManualRef */
        ManualRef: {
            /** Cause */
            cause?: string | null;
            /** Effect */
            effect?: string | null;
            /** Recovery */
            recovery?: string | null;
            /** Url */
            url?: string | null;
        };
        /** MessageRequest */
        MessageRequest: {
            /** Text */
            text: string;
            /** Actor */
            actor: string;
        };
        /** MetricSeries */
        MetricSeries: {
            /** Key */
            key: string;
            /**
             * Points
             * @description [sim_ts, value] pairs, oldest first
             */
            points: [
                string,
                number
            ][];
        };
        /** MetricsResponse */
        MetricsResponse: {
            /** Window S */
            window_s: number;
            /** Series */
            series: components["schemas"]["MetricSeries"][];
        };
        /** N1Status */
        N1Status: {
            /** Safe */
            safe: boolean;
            /** Worst Lost Cpu */
            worst_lost_cpu: number | null;
            /** Worst Survivor Cpu */
            worst_survivor_cpu: number | null;
            /** Worst Survivor Busy */
            worst_survivor_busy: number | null;
            /**
             * Threshold
             * @default 90
             */
            threshold: number;
            /**
             * Text
             * @description e.g. 'N-1 at risk: losing CPU 3 puts CPU 5 at ~96%'
             */
            text: string;
            /**
             * Per Cpu
             * @description lost CPU -> {survivor_cpu, survivor_busy}
             * @default {}
             */
            per_cpu: {
                [key: string]: {
                    [key: string]: number;
                };
            };
        };
        /** NormalizedEvent */
        NormalizedEvent: {
            /** Id */
            id: string;
            /** Sim Ts */
            sim_ts: string;
            /** System */
            system: string;
            /** Process */
            process: string;
            /** Subsystem */
            subsystem: string;
            /** Event Number */
            event_number: number;
            /** Critical */
            critical: boolean;
            /** Severity */
            severity: number;
            /** Text */
            text: string;
            /** Raw */
            raw: string;
            /**
             * Fields
             * @default {}
             */
            fields: {
                [key: string]: unknown;
            };
            /** Component Id */
            component_id: string | null;
            /** Fingerprint */
            fingerprint: string;
            /** Episode Id */
            episode_id: string | null;
            /**
             * Quarantined
             * @default false
             */
            quarantined: boolean;
            /**
             * Simulated
             * @description True when the message is invented (not from the HPE manual)
             */
            simulated: boolean;
        };
        /** OptionStep */
        OptionStep: {
            /** Catalog Id */
            catalog_id: string;
            /** Params */
            params: {
                [key: string]: unknown;
            };
            /** Rendered */
            rendered: string;
            /**
             * Tier
             * @enum {string}
             */
            tier: "T0" | "T1" | "T2" | "T3";
            /** Undo */
            undo?: string | null;
        };
        /** PersonRef */
        PersonRef: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** At */
            at?: string | null;
        };
        /** PlanBody */
        PlanBody: {
            /** Request */
            request: string;
            /** Rationale */
            rationale: string;
            /** Steps */
            steps: components["schemas"]["PlanStepItem"][];
        };
        /** PlanCard */
        PlanCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "plan";
            body: components["schemas"]["PlanBody"];
        };
        /** PlanStepItem */
        PlanStepItem: {
            /** Step Id */
            step_id: string;
            /** Catalog Id */
            catalog_id: string;
            /** Rendered */
            rendered: string;
            /**
             * Tier
             * @enum {string}
             */
            tier: "T0" | "T1" | "T2" | "T3";
            /**
             * Parallel Group
             * @default 0
             */
            parallel_group: number;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Card Id */
            card_id?: string | null;
        };
        /** Playbook */
        Playbook: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Version */
            version: number;
            /** Author */
            author: string;
            /** Author Name */
            author_name?: string | null;
            /** Verified By */
            verified_by: {
                [key: string]: unknown;
            }[];
            /**
             * Synthetic
             * @default true
             */
            synthetic: boolean;
            /**
             * Trigger
             * @default {}
             */
            trigger: {
                [key: string]: unknown;
            };
            /** Steps */
            steps: {
                [key: string]: unknown;
            }[];
        };
        /** PlaybooksResponse */
        PlaybooksResponse: {
            /** Playbooks */
            playbooks: components["schemas"]["Playbook"][];
        };
        /** PoliciesResponse */
        PoliciesResponse: {
            /** Version */
            version: number;
            /** Document */
            document: string;
            /** Rules */
            rules: {
                [key: string]: unknown;
            }[];
            /** Protected Processes */
            protected_processes: string[];
            /** Limits */
            limits: {
                [key: string]: unknown;
            };
            /** Read Only */
            read_only: boolean;
        };
        /** PolicyDecision */
        PolicyDecision: {
            /**
             * Effect
             * @enum {string}
             */
            effect: "allow_auto" | "require_approval" | "deny";
            /** Required Approvers */
            required_approvers: number;
            /**
             * Required Roles
             * @default []
             */
            required_roles: ("operator" | "senior" | "expert" | "steward")[];
            /**
             * At Least One Of
             * @default []
             */
            at_least_one_of: ("operator" | "senior" | "expert" | "steward")[];
            /** Rule Ids */
            rule_ids: string[];
            /** Explanation */
            explanation: string;
            /** Escalation */
            escalation?: string | null;
        };
        /** PostmortemBody */
        PostmortemBody: {
            /** Incident Id */
            incident_id: string;
            /** Summary */
            summary: string;
            /** Impact */
            impact: string;
            /** Timeline Md */
            timeline_md: string;
            /** Cause */
            cause: string;
            /** Actions */
            actions: string[];
            /** Follow Ups */
            follow_ups: string[];
        };
        /** PostmortemCard */
        PostmortemCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "postmortem";
            body: components["schemas"]["PostmortemBody"];
        };
        /** PostmortemResponse */
        PostmortemResponse: {
            /** Incident Id */
            incident_id: string;
            /** Summary */
            summary: string;
            /** Impact */
            impact: string;
            /** Timeline Md */
            timeline_md: string;
            /** Cause */
            cause: string;
            /** Actions */
            actions: string[];
            /** Follow Ups */
            follow_ups: string[];
            /**
             * Source
             * @description Model ID, 'replay' or 'fallback'
             */
            source: string;
            /** Created Sim Ts */
            created_sim_ts: string;
        };
        /** ReadOnlyRequest */
        ReadOnlyRequest: {
            /** Enabled */
            enabled: boolean;
            /** Actor */
            actor: string;
        };
        /** Recommender */
        Recommender: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "playbook" | "claim" | "library";
            /** Id */
            id: string;
            /** Author */
            author?: string | null;
            /**
             * Verified By
             * @default []
             */
            verified_by: string[];
        };
        /** ResumeRequest */
        ResumeRequest: {
            /** Interrupt Id */
            interrupt_id: string;
            /** Response */
            response: {
                [key: string]: unknown;
            };
            /** Actor */
            actor: string;
        };
        /** RunAccepted */
        RunAccepted: {
            /** Run Id */
            run_id: string;
            /** Thread Id */
            thread_id: string;
        };
        /** Signal */
        Signal: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /** Component Id */
            component_id: string;
            /** Started At */
            started_at: string;
            /** Ended At */
            ended_at?: string | null;
            /** Value */
            value?: number | null;
            /**
             * Detail
             * @default
             */
            detail: string;
        };
        /** SimClockRequest */
        SimClockRequest: {
            /**
             * Speed
             * @description 1, 2, 4, 8 or 16
             */
            speed?: number | null;
            /** Paused */
            paused?: boolean | null;
            /**
             * Step
             * @description Advance N sim-seconds while paused
             */
            step?: number | null;
            /** Actor */
            actor: string;
        };
        /** SimInjectRequest */
        SimInjectRequest: {
            /**
             * Fault
             * @enum {string}
             */
            fault: "cpu_halt" | "audit_pressure" | "maxservers_change" | "runaway_batch";
            /**
             * Params
             * @description cpu_halt: {cpu}; maxservers_change: {server_class, value}; audit_pressure: {factor}
             * @default {}
             */
            params: {
                [key: string]: unknown;
            };
            /** Actor */
            actor: string;
        };
        /** SimReplayRequest */
        SimReplayRequest: {
            /**
             * Mode
             * @enum {string}
             */
            mode: "off" | "record" | "replay";
            /** Actor */
            actor: string;
        };
        /** SimStartRequest */
        SimStartRequest: {
            /**
             * Scenario
             * @enum {string}
             */
            scenario: "S0" | "S1" | "S2" | "S3" | "S4";
            /**
             * Profile
             * @default demo
             * @enum {string}
             */
            profile: "demo" | "test";
            /** Seed */
            seed?: number | null;
            /** Speed */
            speed?: number | null;
            /** Actor */
            actor: string;
        };
        /** SimState */
        SimState: {
            /** Scenario */
            scenario: string | null;
            /** Scenario Name */
            scenario_name: string | null;
            /**
             * Profile
             * @enum {string}
             */
            profile: "demo" | "test";
            /** Seed */
            seed: number;
            /** Sim Ts */
            sim_ts: string | null;
            /** Speed */
            speed: number;
            /** Paused */
            paused: boolean;
            /** Running */
            running: boolean;
            /**
             * Active Faults
             * @default []
             */
            active_faults: components["schemas"]["ActiveFault"][];
            /** Calendar */
            calendar?: string | null;
        };
        /** SimStateResponse */
        SimStateResponse: {
            /** Scenario */
            scenario: string | null;
            /** Scenario Name */
            scenario_name: string | null;
            /**
             * Profile
             * @enum {string}
             */
            profile: "demo" | "test";
            /** Seed */
            seed: number;
            /** Sim Ts */
            sim_ts: string | null;
            /** Speed */
            speed: number;
            /** Paused */
            paused: boolean;
            /** Running */
            running: boolean;
            /**
             * Active Faults
             * @default []
             */
            active_faults: components["schemas"]["ActiveFault"][];
            /** Calendar */
            calendar?: string | null;
        };
        /** Situation */
        Situation: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Severity */
            severity: number;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "updating" | "stable" | "resolved";
            origin: components["schemas"]["SituationOrigin"];
            /** Components */
            components: string[];
            /** Services */
            services: string[];
            counts: components["schemas"]["SituationCounts"];
            /** Template */
            template: string;
            /** First At */
            first_at: string;
            /** Last At */
            last_at: string;
            /** Incident Id */
            incident_id: string | null;
            /**
             * Suggested Playbooks
             * @default []
             */
            suggested_playbooks: string[];
        };
        /** SituationBody */
        SituationBody: {
            /** Situation Id */
            situation_id: string;
            /** Severity */
            severity: number;
            /** Components */
            components: string[];
            /** Services */
            services: string[];
            counts: components["schemas"]["SituationCounts"];
            /**
             * Collapse Text
             * @description e.g. '612 events → 1 situation'
             */
            collapse_text: string;
            /** Template */
            template: string;
            /** First At */
            first_at: string;
            /** Age S */
            age_s: number;
            /**
             * Suggested Playbooks
             * @default []
             */
            suggested_playbooks: string[];
        };
        /** SituationCard */
        SituationCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "situation";
            body: components["schemas"]["SituationBody"];
        };
        /** SituationCounts */
        SituationCounts: {
            /** Raw Events */
            raw_events: number;
            /** Episodes */
            episodes: number;
            /** Signals */
            signals: number;
        };
        /** SituationDetail */
        SituationDetail: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Severity */
            severity: number;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "updating" | "stable" | "resolved";
            origin: components["schemas"]["SituationOrigin"];
            /** Components */
            components: string[];
            /** Services */
            services: string[];
            counts: components["schemas"]["SituationCounts"];
            /** Template */
            template: string;
            /** First At */
            first_at: string;
            /** Last At */
            last_at: string;
            /** Incident Id */
            incident_id: string | null;
            /**
             * Suggested Playbooks
             * @default []
             */
            suggested_playbooks: string[];
            /**
             * Episodes
             * @default []
             */
            episodes: components["schemas"]["Episode"][];
            /**
             * Signals
             * @default []
             */
            signals: components["schemas"]["Signal"][];
        };
        /** SituationOrigin */
        SituationOrigin: {
            /** Component Id */
            component_id: string;
        };
        /** SituationsResponse */
        SituationsResponse: {
            /** Situations */
            situations: components["schemas"]["Situation"][];
        };
        /** StopRule */
        StopRule: {
            /** Met */
            met: boolean;
            /** Top */
            top: number;
            /** Margin */
            margin: number;
            /** Reason */
            reason?: string | null;
        };
        /** SystemStatus */
        SystemStatus: {
            /**
             * System
             * @default \TORBANK
             */
            system: string;
            sim: components["schemas"]["SimState"];
            /**
             * Llm Provider
             * @enum {string}
             */
            llm_provider: "nemotron" | "none";
            /** Model Fast */
            model_fast: string | null;
            /** Model Strong */
            model_strong: string | null;
            /**
             * Replay Mode
             * @enum {string}
             */
            replay_mode: "off" | "record" | "replay";
            /**
             * Embeddings
             * @enum {string}
             */
            embeddings: "local" | "none";
            /** Read Only */
            read_only: boolean;
            /** Contract Version */
            contract_version: string;
        };
        /** TerminalInputRequest */
        TerminalInputRequest: {
            /** Line */
            line: string;
            /** Actor */
            actor: string;
        };
        /** TerminalInputResponse */
        TerminalInputResponse: {
            /** Accepted */
            accepted: boolean;
            /** Message */
            message: string;
            /** Catalog Id */
            catalog_id?: string | null;
            /** Exec Id */
            exec_id?: string | null;
            /** Card Id */
            card_id?: string | null;
            /** Thread Id */
            thread_id?: string | null;
        };
        /** TextBody */
        TextBody: {
            /** Markdown */
            markdown: string;
            /**
             * Sentences
             * @description [{text, citation_ids[]}] when the answer is sentence-cited
             * @default []
             */
            sentences: {
                [key: string]: unknown;
            }[];
            /**
             * Unknown
             * @default false
             */
            unknown: boolean;
            /** Ask Whom */
            ask_whom?: string | null;
            /**
             * Link
             * @description e.g. {label: 'Open Incident Room', incident_id: 'inc_...'}
             */
            link?: {
                [key: string]: string;
            } | null;
            /**
             * Alternatives
             * @description Nearest safe catalog alternatives for 'not in catalog'
             * @default []
             */
            alternatives: {
                [key: string]: unknown;
            }[];
        };
        /** TextCard */
        TextCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "text";
            body: components["schemas"]["TextBody"];
        };
        /** Thread */
        Thread: {
            /** Id */
            id: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "ask" | "command" | "investigate";
            /** Actor */
            actor: string;
            /** Incident Id */
            incident_id: string | null;
            /** Title */
            title: string;
            /**
             * Status
             * @enum {string}
             */
            status: "idle" | "running" | "waiting" | "done" | "failed";
            /** Created At */
            created_at: string;
        };
        /** ThreadCreateRequest */
        ThreadCreateRequest: {
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "ask" | "command" | "investigate";
            /** Incident Id */
            incident_id?: string | null;
            /** Actor */
            actor: string;
        };
        /** ThreadDetail */
        ThreadDetail: {
            thread: components["schemas"]["Thread"];
            /** Cards */
            cards: (components["schemas"]["TextCard"] | components["schemas"]["SituationCard"] | components["schemas"]["CommandCard"] | components["schemas"]["PlanCard"] | components["schemas"]["HypothesesCard"] | components["schemas"]["EvidenceCard"] | components["schemas"]["ExpertCard"] | components["schemas"]["DecisionCard"] | components["schemas"]["VerificationCard"] | components["schemas"]["EscalationCard"] | components["schemas"]["PostmortemCard"] | components["schemas"]["ClaimReviewCard"])[];
            /** Trace */
            trace: components["schemas"]["TraceStep"][];
            /** Pending Interrupts */
            pending_interrupts: components["schemas"]["Interrupt"][];
        };
        /** TimelineItem */
        TimelineItem: {
            /** Id */
            id: string;
            /** Incident Id */
            incident_id: string;
            /** Sim Ts */
            sim_ts: string;
            /** Wall Ts */
            wall_ts: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "situation" | "episode" | "check" | "hypothesis_change" | "approval_requested" | "approval_decided" | "action_executed" | "undo" | "verification" | "note" | "status_change" | "claim_drafted";
            actor: components["schemas"]["ActorRef"];
            /** Title */
            title: string;
            /**
             * Detail
             * @default
             */
            detail: string;
            ref?: components["schemas"]["TimelineRef"] | null;
        };
        /** TimelineRef */
        TimelineRef: {
            /**
             * Type
             * @enum {string}
             */
            type: "card" | "execution" | "approval" | "situation" | "episode" | "claim" | "incident" | "run";
            /** Id */
            id: string;
        };
        /** TimelineResponse */
        TimelineResponse: {
            /** Items */
            items: components["schemas"]["TimelineItem"][];
        };
        /** Topology */
        Topology: {
            /** Nodes */
            nodes: components["schemas"]["TopologyNode"][];
            /** Edges */
            edges: components["schemas"]["TopologyEdge"][];
        };
        /** TopologyEdge */
        TopologyEdge: {
            /** Source */
            source: string;
            /** Target */
            target: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "runs_on" | "backup_on" | "serves" | "depends_on" | "writes_audit_to" | "uses_volume";
        };
        /** TopologyNode */
        TopologyNode: {
            /** Id */
            id: string;
            /**
             * Type
             * @enum {string}
             */
            type: "system" | "cpu" | "process" | "server_class" | "tmf" | "volume" | "service";
            /** Name */
            name: string;
            /**
             * Attributes
             * @default {}
             */
            attributes: {
                [key: string]: unknown;
            };
            /**
             * Tags
             * @default []
             */
            tags: string[];
        };
        /** TraceDetail */
        TraceDetail: {
            /**
             * Tools
             * @default []
             */
            tools: string[];
            /**
             * Evidence Ids
             * @default []
             */
            evidence_ids: string[];
            /**
             * Model
             * @description '<model id>' | 'replay' | 'fallback' | null when no model is involved
             */
            model?: string | null;
            /** Prompt Hash */
            prompt_hash?: string | null;
            /** Inputs */
            inputs?: string | null;
            /** Output */
            output?: string | null;
        };
        /** TraceStep */
        TraceStep: {
            /** Run Id */
            run_id: string;
            /** Step Id */
            step_id: string;
            /** Node */
            node: string;
            /** Label */
            label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "done" | "waiting" | "failed" | "fallback";
            /** Started At */
            started_at: string;
            /** Duration Ms */
            duration_ms: number | null;
            /** Summary */
            summary: string;
            detail: components["schemas"]["TraceDetail"];
        };
        /** UndoEntry */
        UndoEntry: {
            /** Id */
            id: string;
            /** Execution Id */
            execution_id: string;
            /** Catalog Id */
            catalog_id: string;
            /** Params */
            params: {
                [key: string]: unknown;
            };
            /** Rendered */
            rendered: string;
            /** Label */
            label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "applied" | "discarded";
            /** Created Sim Ts */
            created_sim_ts: string;
        };
        /** UndoResponse */
        UndoResponse: {
            /** Accepted */
            accepted: boolean;
            /** Message */
            message: string;
            /** Approval Id */
            approval_id?: string | null;
            /** Exec Id */
            exec_id?: string | null;
        };
        /** UndoSpec */
        UndoSpec: {
            /** Catalog Id */
            catalog_id: string;
            /** Params */
            params: {
                [key: string]: unknown;
            };
            /** Rendered */
            rendered: string;
        };
        /** User */
        User: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /**
             * Role
             * @enum {string}
             */
            role: "operator" | "senior" | "expert" | "steward";
            /** Initials */
            initials: string;
            /** Title */
            title: string;
        };
        /** UsersResponse */
        UsersResponse: {
            /** Users */
            users: components["schemas"]["User"][];
        };
        /** VerificationBody */
        VerificationBody: {
            /** Failure Mode */
            failure_mode: string;
            /** Criteria */
            criteria: components["schemas"]["VerificationCriterion"][];
            /** Window S */
            window_s: number;
            /** Window Start Sim Ts */
            window_start_sim_ts: string;
            /** Window End Sim Ts */
            window_end_sim_ts: string | null;
            /**
             * Result
             * @enum {string}
             */
            result: "pending" | "recovered" | "not_recovered" | "regression";
            /** Summary */
            summary: string;
            /**
             * Propose Undo
             * @description Undo entry IDs to offer on regression
             * @default []
             */
            propose_undo: string[];
        };
        /** VerificationCard */
        VerificationCard: {
            /** Id */
            id: string;
            /** Thread Id */
            thread_id: string | null;
            /** Incident Id */
            incident_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "info" | "proposed" | "awaiting_approval" | "partially_approved" | "auto_running" | "running" | "done" | "failed" | "blocked" | "rejected" | "expired" | "resolved";
            /** Title */
            title: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["Citation"][];
            /**
             * Actions
             * @default []
             */
            actions: ("approve" | "edit" | "reject" | "undo" | "investigate" | "open_incident" | "approve_selected" | "approve_all_readonly" | "propose_undo" | "copy_summary" | "confirm" | "edit_confirm" | "open_source" | "open_incident_room")[];
            /**
             * Source
             * @description Model ID, 'replay', 'fallback', or null when no model was used
             */
            source?: string | null;
            /** Created At */
            created_at: string;
            /** Sim Ts */
            sim_ts: string | null;
            /**
             * Seq
             * @description Order within the thread; cards render sorted by seq
             * @default 0
             */
            seq: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "verification";
            body: components["schemas"]["VerificationBody"];
        };
        /** VerificationCriterion */
        VerificationCriterion: {
            /** Text */
            text: string;
            /** Met */
            met: boolean;
            /** Value */
            value?: string | null;
        };
        /** WhatIfRequest */
        WhatIfRequest: {
            /** Actions */
            actions: {
                [key: string]: unknown;
            }[];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    system_status_api_system_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemStatus"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    system_read_only_api_system_read_only_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReadOnlyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemStatus"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    users_api_users_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UsersResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    sim_state_api_sim_state_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimStateResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    sim_start_api_sim_start_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SimStartRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimStateResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    sim_inject_api_sim_inject_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SimInjectRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimStateResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    sim_clock_api_sim_clock_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SimClockRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimStateResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    sim_reset_api_sim_reset_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActorOnly"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimStateResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    sim_replay_api_sim_replay_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SimReplayRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemStatus"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    topology_api_topology_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Topology"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    health_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    metrics_api_metrics_get: {
        parameters: {
            query?: {
                keys?: string;
                window_s?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MetricsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    events_api_events_get: {
        parameters: {
            query?: {
                limit?: number;
                quarantined?: boolean | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    episodes_api_episodes_get: {
        parameters: {
            query?: {
                status?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EpisodesResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    situations_api_situations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SituationsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    situation_api_situations__situation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                situation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SituationDetail"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    investigate_api_situations__situation_id__investigate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                situation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActorOnly"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvestigateResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_thread_api_threads_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ThreadCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Thread"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    thread_detail_api_threads__thread_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                thread_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThreadDetail"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    post_message_api_threads__thread_id__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                thread_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunAccepted"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    resume_api_threads__thread_id__resume_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                thread_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResumeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunAccepted"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    approvals_api_approvals_get: {
        parameters: {
            query?: {
                status?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApprovalsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    decide_api_approvals__approval_id__decide_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                approval_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApprovalDecideRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApprovalDecideResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    catalog_api_catalog_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CatalogResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    preview_api_commands_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommandPreviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandPreviewResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    terminal_input_api_terminal_input_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TerminalInputRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TerminalInputResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    execution_api_executions__exec_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                exec_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Execution"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    undo_api_executions__exec_id__undo_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                exec_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActorOnly"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UndoResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    incidents_api_incidents_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    incident_api_incidents__incident_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentDetail"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    timeline_api_incidents__incident_id__timeline_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TimelineResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    postmortem_api_incidents__incident_id__postmortem_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PostmortemResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    close_incident_api_incidents__incident_id__close_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActorOnly"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Incident"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    whatif_api_incidents__incident_id__whatif_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WhatIfRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    kb_search_api_kb_search_get: {
        parameters: {
            query: {
                q: string;
                k?: number;
                types?: string | null;
                debug?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbSearchResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    kb_item_api_kb_items__item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbItem"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    claims_api_claims_get: {
        parameters: {
            query?: {
                status?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClaimsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    review_claim_api_claims__claim_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                claim_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ClaimReviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Claim"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    playbooks_api_playbooks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlaybooksResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    playbook_api_playbooks__playbook_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                playbook_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Playbook"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    ledger_api_ledger_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LedgerResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    ledger_grant_api_ledger__key__grant_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LedgerGrantRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LedgerEntry"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    ledger_revoke_api_ledger__key__revoke_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LedgerRevokeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LedgerEntry"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    policies_api_policies_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PoliciesResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    audit_api_audit_get: {
        parameters: {
            query?: {
                limit?: number;
                incident_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    audit_verify_api_audit_verify_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditVerify"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    eval_latest_api_eval_latest_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EvalLatestResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    eval_run_api_eval_run_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["EvalRunRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EvalRunAccepted"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}
