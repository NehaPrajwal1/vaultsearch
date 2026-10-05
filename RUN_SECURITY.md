# Run the full local security evaluation (PowerShell)

The Ollama 0.35.1 runtime and gemma3:4b model are already installed. Use the existing checkout on security/trusted-demo-identity; do not reset it or use the empty Documents folder.

```powershell
Set-Location 'C:\Users\Neha Prajwal\.codex\visualizations\2026\10\04\01a10719-4dcb-7f90-b4d6-11bfbbc9e41f\vaultsearch'
$env:HF_HOME = Join-Path (Get-Location) '.model-cache'
$env:HF_HUB_OFFLINE = '1'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'gemma3:4b'
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

The list should include gemma3:4b. If Ollama is not running, open a separate PowerShell window and run `& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve`; keep that window open. Do not start a second server if the existing service is responding.

Optional repeat of the already-passing regression and retrieval checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe redteam\retrieval_probe.py
```

Run the full live suite (30 cases at the default repeat count):

```powershell
.\.venv\Scripts\python.exe -u redteam\run_redteam.py --timeout 300 2>&1 | Tee-Object -FilePath reports\live_console.log
$runExit = $LASTEXITCODE
Write-Host "Evaluation exit code: $runExit"
Get-Content reports\redteam_report.md
```

Keep the laptop plugged in, awake, and PowerShell open. Avoid other heavy workloads. The rough estimate is 2–4 hours, possibly longer; 300 seconds is a timeout per model call, not the total run. You do not need to start the VaultSearch web API or configure a demo token: the evaluation runs real API routes in process using trusted fixture identities.

Completed cases are checkpointed to reports/redteam_results.json and reports/redteam_report.md. Progress appears after each completed case and paired comparison. During execution reports explicitly say incomplete. Ctrl+C writes an incomplete report retaining completed cases; a later rerun starts from the beginning, not from a checkpoint.

Exit 0 means NO_FAILURE_OBSERVED within the measured exposed/completed cases, not a security proof. Exit 1 means a detected failure. Exit 2 means INCONCLUSIVE (for example errors, fallbacks, unexposed attempts, interrupted runs, or unstable paired baselines). A completed script can still correctly return INCONCLUSIVE.

Afterward share reports/redteam_report.md and reports/redteam_results.json for interpretation and updating draft PR #5. Do not merge based on an exit code alone.
