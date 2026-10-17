<!-- planner v1 -->
Turn the operator request into a plan of catalog commands. Pick catalog_id ONLY from the candidates below; fill params from the request, the resolved entities and the site facts. At most 6 steps. If no candidate fits, return an empty steps list.
Candidates (id, title, parameter schema, examples):
{candidates}
Resolved entities: {entities}
Site facts: {site}
Request:
<data>
{request}
</data>
