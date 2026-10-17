# Baton content pack

All expert, incident, glossary, concept and command-reference records are synthetic and scoped to the TORBANK demonstration. Each carries `synthetic: true` and a source link. YAML files use JSON syntax, which is valid YAML 1.2.

`operator_messages.jsonl` uses the explicitly permitted MVP Appendix A fallback, with real HPE message identifiers, MVP-provided templates, and short synthetic annotations. Simplified templates and simulated state words are identified. This is not a full manual crawl; see `manifest.json` for counts and limitations.

Sources: [HPE message format and EMS](https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch01.html), [OMF](https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch68.html), [PATHWAY](https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch78.html). The product-specific operational guidance comes from the supplied MVP specification, not a claim about production systems.

Regenerate the original seeds with `node frontend/tools/generate-content.mjs` from the repository root. This overwrites these seed files; do not run it over curated human edits. It also refreshes the frontend's rehearsal content snapshot.
