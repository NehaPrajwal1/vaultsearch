> **Current state (2026-10-07): all 30 cases are saved.** No further resume commands are needed. The canonical final report is `reports/redteam_report.md`; status is INCONCLUSIVE because of timeouts, unexposed attempts, and unstable live paired baselines. The instructions below are retained for future interrupted runs.

# Continue after the interrupted Windows run

Windows Memory Diagnostic reported no errors. The cause of the 0x12B crash is still undiagnosed. Do not immediately repeat the original multi-hour command. The saved checkpoint contains 22/30 cases: 16 completed and 6 incomplete due to timeouts. Eight unattempted cases remain. The report stays INCONCLUSIVE; resuming preserves the timeouts and unexposed attempts.

## One-case batch (PowerShell)

```powershell
Set-Location 'C:\Users\Neha Prajwal\.codex\visualizations\2026\10\04\01a10719-4dcb-7f90-b4d6-11bfbbc9e41f\vaultsearch'
$env:HF_HOME = Join-Path (Get-Location) '.model-cache'
$env:HF_HUB_OFFLINE = '1'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'gemma3:4b'

# First batch resumes the preserved original run:
.\.venv\Scripts\python.exe -u redteam\resume_redteam.py --resume-from reports\redteam_results.json --max-cases 1 --timeout 300
```

Ollama must be running with gemma3:4b installed. No separate VaultSearch API server is needed. Keep the laptop plugged in on a hard surface, close unused heavy apps, and remain available during this first batch. One case can still take several minutes and contain multiple 300-second model-call timeouts. This does not cure a driver/firmware/hardware problem or guarantee stability.

The next batch must resume the NEW checkpoint, not the original 22-case report:

```powershell
.\.venv\Scripts\python.exe -u redteam\resume_redteam.py --resume-from reports\resumed-live\redteam_results.json --max-cases 1 --timeout 300
Get-Content reports\resumed-live\redteam_report.md
```

Repeat this second command after checking each batch until Saved 30/30 appears. The one-case batch limit intentionally returns exit 2 while work remains. Existing timeouts/unexposed cases may keep the final result inconclusive even with all 30 attempted. They are retained rather than silently retried or turned into passes. If another system crash occurs, stop model testing and investigate Windows crash-dump/driver/firmware causes before continuing.

The runner rejects incompatible model digests, Python/packages, application/indexing code, indexes, or identity data. A change of model requires a separate evaluation. Runner versions and timestamps are recorded per resumed session; original metadata/results are retained. Completed paired samples from the original run are kept; fresh repeated-baseline comparisons still test whether non-timing outputs actually match across the resumed sessions. Do not compare new results as a single-session timing experiment.

Original checkpoint backups are under reports/interrupted-2026-10-05/. Resumed outputs are separate under reports/resumed-live/. Ctrl+C preserves completed new cases. The application remains a portfolio demo and draft PR #5 is unmerged.

---

# Original full-run instructions (only for a deliberate NEW evaluation)

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
