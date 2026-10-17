# Baton content pack

All expert, incident, glossary, concept and command-reference records are synthetic and scoped to the TORBANK demonstration. Each carries `synthetic: true` and a source link. YAML files use JSON syntax, which is valid YAML 1.2.

`operator_messages.jsonl` contains a 150-record selection: 147 real HPE messages from chapters 68 (OMF) and 78 (PATHWAY), plus three synthetic APP chatter records. Cause, effect and recovery come from the manual. The simulator's Appendix A templates are preserved from `data/rules/ems_messages.yaml`, including simplified layouts and simulated state words, and remain marked `synthetic: true`. New manual templates convert replaceable spans to named variables; their default severity hint (2) is a retrieval/display convention, not an HPE severity classification. This is a bounded selection, not the entire manual.

Run `.venv\Scripts\python.exe scripts/fetch_opmsgs.py` to merge records. Raw HTML is cached under ignored `var/opmsgs_cache/`; `--offline` requires no network, and `--refresh` tries to update the cache with cached fallback on failure. Without either a reachable source or a cache, existing fallback records stay present. Counts print to the console and update `manifest.json`. Selection is balanced between chapters, with existing records always retained; `--chapters 68 78 15 121` optionally includes common and TMF messages. The committed pack needs no cache to seed the backend.

Sources: [HPE message format and EMS](https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch01.html), [OMF](https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch68.html), [PATHWAY](https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch78.html). The product-specific operational guidance comes from the supplied MVP specification, not a claim about production systems.

Regenerate the original seeds with `node frontend/tools/generate-content.mjs` from the repository root. This overwrites these seed files, including the fetched manual selection; do not run it over curated human edits or the fetched pack. It also refreshes the frontend's rehearsal content snapshot.
