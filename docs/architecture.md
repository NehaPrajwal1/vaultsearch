# Architecture and trust boundaries

## Default search path

1. Synthetic source records are normalized and chunked. Each chunk retains its document's allowed principals.
2. The operator configures a known persona and bearer token. The API derives the request identity from this configuration.
3. Identity groups expand into principals. ACL code selects permitted chunk IDs.
4. BM25 is computed on the permitted corpus, with stable chunk-ID tie breaking.
5. The API returns ranked excerpts and identifiers. The UI renders source content as untrusted text.

MCP uses this same HTTP boundary. Its tool schema offers no persona selector.

```mermaid
sequenceDiagram
    participant Client as Browser or MCP
    participant API as FastAPI
    participant ACL as Identity and ACL
    participant Search as Retriever
    Client->>API: Query and bearer token
    API->>API: Validate token; reject conflicting identity
    API->>ACL: Expand configured persona
    ACL-->>Search: Permitted chunk set
    API->>Search: Query
    Search->>Search: BM25 over permitted corpus
    Search-->>API: Ranked permitted excerpts
    API-->>Client: Text, source and stable IDs
```

## Optional answer path

The orchestrator plans queries and selects permitted evidence within an evidence budget. Model synthesis receives untrusted source data. Citation verification constrains labels to selected evidence; an advisory critic evaluates source agreement. The presentation layer replaces flagged drafts with an application-written message and omits risky model-authored fields. Source excerpts remain available.

Authorization is implemented in ordinary application code. Citation membership is not factual verification; groundedness is not a safety verdict. Novel instructions can evade the presentation detector.

## Decisions worth reviewing

| Decision | Benefit | Cost or limitation |
|---|---|---|
| One server-bound identity per demo instance | Easy-to-audit identity boundary | Restart to switch personas; no enterprise authentication |
| ACL selection before ranking | Restricted chunks excluded from permitted results | Depends on accurate ACL metadata and trusted operator configuration |
| BM25 statistics from permitted corpus | Avoids global hidden-corpus ranking dependence in this path | Recomputes statistics; no large-scale performance claim |
| Search without a model by default | Small runtime and dependable demonstration | Keyword matching has semantic limitations |
| Fixed response for flagged drafts | Risky drafts are not redisplayed | False positives and semantic evasions remain |
| Source manifests and isolated evidence directories | Separates code versions and test types | Modified snapshots need new provenance |

## Scope of trust

Operators control identity configuration, tokens, ACLs and local files. Bearer-token possession represents the configured persona. Names and group memberships in the directory endpoint are intentionally visible to authenticated demo users; restricted document visibility counts are not shared there.

Timing channels, host compromise, erroneous upstream permissions and large-scale multi-user deployment have not been established as safe by this demo.
