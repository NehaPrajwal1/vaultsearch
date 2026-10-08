# Five-minute synthetic demo

After setup, start with `python run_demo.py --user ines` using the project virtual environment; copy the printed token into Connect. No model service is needed. Start as `user:ines` and connect using the fresh operator token.

1. Open **Search evidence** (the default tab). Search `paid time off`. Open **Read source excerpt (untrusted)**. Check the policy text, document ID and chunk ID. These are retrieved sources, not a generated answer.
2. Search `Q3 infrastructure budget`. Inspect every returned excerpt. The engineering persona must not receive finance-only budget evidence. A result or its absence is not a statement about whether restricted documents exist.
3. Stop the server. Run `python run_demo.py --user dmitri` with the project virtual environment, then reconnect using its newly printed token. Search the same budget question. The finance persona can inspect its permitted budget evidence. Old-token and conflicting-identity requests are rejected.
4. Search `zygomorphic quasar`. Explain the empty result as “no matching permitted keyword evidence,” without making a hidden-document existence claim. Try ordinary keywords from a known document to recover.
5. Open **Generated draft**. In search-only mode it is explicitly disabled; search continues working. Discuss the optional model mode using the containment replay summary below rather than loading a model on this laptop.

## Explaining generated-answer limitations

The eight recorded Colab answers are replayed offline: ordinary onboarding guidance stays visible; access-override and credential-export drafts receive a fixed message; legitimate security quotations also receive it (known false positives). Original raw calls remain in local evaluation artifacts. No live improvement is claimed.

When generation is deliberately enabled elsewhere, citations scroll to the full permitted excerpt and can be compared with the claim. “Grounded” measures agreement with source text; a malicious source can support unsafe advice. A missing warning is not a safety approval. A model outage gives an unavailable answer state while keyword search stays usable.

## Reproduce the checks

Run `python redteam/release_check.py` with the project virtual environment and `requirements-test.txt` installed. Read the new `validation.json`, `acceptance.json`, `retrieval-pairs.json`, and optional `offline-replay.json`. Preserve earlier output directories. These are deterministic/scripted checks, distinct from live-model measurements.

Nothing is published by startup or validation. Stop the local server after the demonstration.

## Optional scripted browser verification

For UI development without a model, `tests/scripted_ui_server.py` serves the real UI/API with a tiny synthetic corpus and scripted outputs on `127.0.0.1:8766`. Set `VAULTSEARCH_USER=user:ines` and a fresh `VAULTSEARCH_TOKEN` before starting it. This is explicitly a QA fixture, not a live-model demonstration. Queries: `paid days` gives a cited draft; `migration checklist` gives a withheld draft; `paid days unavailable` simulates synthesis failure. Keyword search remains usable and a later `paid days` request recovers. Stop the process after inspection.
