"""Create local Colab artifacts; nothing is uploaded or executed remotely."""
import ast, hashlib, importlib.metadata, json, subprocess, sys, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT/'.local-evaluations'/('colab-'+stamp)
    out.mkdir(parents=True)
    selected = [*ROOT.glob('app/*.py'), *ROOT.glob('redteam/*.py'), *ROOT.glob('web/*')]
    selected += [ROOT/n for n in ('indexes/chunks_meta.json','data/users_groups.json','data/sources/injections.json','data/chunks.json','tests/test_api_probe.py','tests/test_redteam.py','tests/test_tools.py','tests/test_presentation.py')]
    contents = {p.relative_to(ROOT).as_posix():p.read_bytes() for p in selected if p.is_file() and p.name != 'build_colab_bundle.py'}
    packages = ('numpy','rank-bm25','faiss-cpu','fastapi','httpx','pytest')
    contents['colab-requirements.txt'] = ('\n'.join(n+'=='+importlib.metadata.version(n) for n in packages)+'\n').encode()
    manifest = {'created_utc':stamp,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'files':{n:hashlib.sha256(d).hexdigest() for n,d in sorted(contents.items())}}
    contents['BUNDLE_MANIFEST.json'] = json.dumps(manifest,indent=2).encode()
    bundle = out/'vaultsearch-colab-bundle.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for n,d in sorted(contents.items()): z.writestr(n,d)
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest()
    cells=[]
    def md(t): cells.append({'cell_type':'markdown','metadata':{},'source':t.splitlines(True)})
    def code(t):
        ast.parse(t)
        cells.append({'cell_type':'code','metadata':{},'source':t.splitlines(True),'execution_count':None,'outputs':[]})
    md('''# VaultSearch: bounded Colab evaluation
Upload sends unpublished code and synthetic fixtures to your Google runtime. Nothing is published to GitHub. Keep the notebook interactive. Do not mount Drive or expose a public server.

This is a **new Linux/GPU/BM25 evaluation**, not a continuation of Windows checkpoints or validation of default hybrid retrieval. Setup downloads pinned Python packages, Ollama 0.35.1 and Gemma 3 4B into Colab. Free GPU availability is not guaranteed. Download results after each case because runtime files are temporary.

Start with one clean benign case. Live execution defaults to disabled so Run all does not start inference. No GPU execution has been validated merely by preparing this notebook.
''')
    code('''import os, sys, json, hashlib, subprocess, time, zipfile, tempfile, io
from pathlib import Path
from google.colab import files
GPU = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader"], text=True)
print(GPU)
assert int(GPU.splitlines()[0].split(",")[2].strip().split()[0]) >= 6000, "Need at least 6 GB free GPU memory"
READY = False
''')
    md('## Upload the matching bundle\nChoose only `vaultsearch-colab-bundle.zip` supplied with this notebook. Its exact hash is checked before extraction.')
    code('''uploaded = files.upload()
assert len(uploaded) == 1, "Upload only the supplied ZIP"
archive_bytes = next(iter(uploaded.values()))
EXPECTED_SHA256 = "'''+digest+'''"
assert hashlib.sha256(archive_bytes).hexdigest() == EXPECTED_SHA256, "Wrong or modified bundle"
ROOT = Path(tempfile.mkdtemp(prefix="vaultsearch-", dir="/content"))
with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
    for member in z.infolist():
        assert (ROOT/member.filename).resolve().is_relative_to(ROOT.resolve()), "Unsafe archive path"
    z.extractall(ROOT)
manifest = json.loads((ROOT/"BUNDLE_MANIFEST.json").read_text())
for name, expected in manifest["files"].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
print("Verified", len(manifest["files"]), "files; source commit:", manifest["commit"], "; modified:", manifest["working_tree_dirty"])
RESULTS = ROOT/".local-evaluations"
RESULTS.mkdir(exist_ok=True)
''')
    md('## Install API/BM25 dependencies and run scripted checks\nNo embedding or reranker model is loaded. If setup fails, share the error instead of silently changing versions.')
    code('''subprocess.run([sys.executable,"-m","pip","install","-q","-r",str(ROOT/"colab-requirements.txt")],check=True,timeout=300)
check = subprocess.run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider","tests/test_api_probe.py","tests/test_presentation.py"],cwd=ROOT,capture_output=True,text=True,timeout=90)
(RESULTS/"colab-scripted-tests.json").write_text(json.dumps({"returncode":check.returncode,"stdout":check.stdout,"stderr":check.stderr},indent=2))
print(check.stdout,check.stderr)
assert check.returncode == 0, "Fix scripted tests before inference"
''')
    md('## Install Ollama 0.35.1 and verify Gemma\nUses the [official versioned installer](https://docs.ollama.com/linux#installing-specific-versions). Downloads several GB into Colab. The server stays on loopback; no tunnel or public endpoint is created.')
    code('''import urllib.request
installer = urllib.request.urlopen("https://ollama.com/install.sh",timeout=30).read()
install_path = ROOT/"ollama-install.sh"
install_path.write_bytes(installer)
import shutil
if shutil.which("zstd") is None:
    subprocess.run(["apt-get", "update", "-qq"], check=True, timeout=180)
    subprocess.run(["apt-get", "install", "-y", "-qq", "zstd"], check=True, timeout=180)
install_log = RESULTS/"ollama-install.log"
with install_log.open("w") as log:
    try:
        install_result = subprocess.run(["sh", str(install_path)], env=dict(os.environ, OLLAMA_VERSION="0.35.1"), stdout=log, stderr=subprocess.STDOUT, timeout=600)
    finally:
        log.flush()
        print(install_log.read_text(errors="replace")[-12000:])
if install_result.returncode != 0:
    raise RuntimeError("Ollama install failed; share the installer output printed above. Full log: " + str(install_log))
os.environ.update(OLLAMA_HOST="127.0.0.1:11434",OLLAMA_URL="http://127.0.0.1:11434",OLLAMA_MODEL="gemma3:4b",OLLAMA_CONTEXT_LENGTH="4096",OLLAMA_NUM_PARALLEL="1",OLLAMA_MAX_LOADED_MODELS="1",OLLAMA_KEEP_ALIVE="60s")
import httpx
try:
    httpx.get("http://127.0.0.1:11434/api/version",timeout=2).raise_for_status()
except httpx.HTTPError:
    server_log = open(RESULTS/"ollama-server.log","a")
    server = subprocess.Popen(["ollama","serve"],env=os.environ.copy(),stdout=server_log,stderr=subprocess.STDOUT)
else:
    raise RuntimeError("An Ollama server already exists. Stop here and inspect it; server settings must be known.")
for attempt in range(30):
    try:
        version = httpx.get("http://127.0.0.1:11434/api/version",timeout=2).json()
        break
    except (httpx.HTTPError,ValueError): time.sleep(1)
else: raise RuntimeError("Ollama did not start; inspect server log")
assert version["version"] == "0.35.1", version
subprocess.run(["ollama","pull","gemma3:4b"],check=True,timeout=1200)
models = httpx.get("http://127.0.0.1:11434/api/tags",timeout=5).json()["models"]
selected = next(m for m in models if m["name"] == "gemma3:4b")
assert selected["digest"] == "a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a", "Model digest differs; stop and share it"
setup = {"python":sys.version,"gpu":GPU,"ollama":version,"model":selected,"installer_sha256":hashlib.sha256(installer).hexdigest(),"bundle_sha256":EXPECTED_SHA256,"server_environment":{k:v for k,v in os.environ.items() if k.startswith("OLLAMA_")},"packages":subprocess.check_output([sys.executable,"-m","pip","freeze"],text=True)}
(RESULTS/"colab-runtime.json").write_text(json.dumps(setup,indent=2))
READY = True
print("Setup ready; no inference has run.")
''')
    md('''## Run ONE case and download results
Set RUN_LIVE_CASE to True when ready. Start with benign / controlled / present. Review that result before changing CASE to access_paraphrase, export_paraphrase, or benign_analysis, one at a time.

For later whole-corpus exposure, use CORPUS="existing" (benign conditions may include background attacks). For an existing-corpus reserve triplet, use CASE="pair-reserve", CORPUS="existing", and VARIANT="present", then "repeat", then "absent", in three separately reviewed runs.

Each enabled case automatically preloads the model with a separate 180-second setup timeout and records GPU placement. No separate preload cell is needed. If the runtime restarts, rerun setup first.

Exit 2 means inconclusive/manual review, not resistance. Inspect actual completion, synthesis exposure, raw answers and false positives. The outer 180-second timeout stops the probe process; stopping the server's model is attempted separately and may add time. Results are downloaded after each attempted case. Save them before disconnecting.
''')
    code('''RUN_LIVE_CASE = False
CASE = "benign"
CORPUS = "controlled"
VARIANT = "present"
if RUN_LIVE_CASE:
    assert globals().get("READY"), "Complete setup first"
    before = set(RESULTS.glob("api-*.json"))
    command = [sys.executable,"redteam/api_probe.py","run","--case",CASE,"--corpus",CORPUS,"--variant",VARIANT,"--timeout","45","--budget","150"]
    stamp = str(time.time_ns())
    try:
        # Setup preload is outside unchanged evaluation call/process budgets.
        preload = {"purpose":"setup only; not evaluation", "status":"started"}
        preload_path = RESULTS/("preload-"+stamp+".json")
        try:
            response = httpx.post("http://127.0.0.1:11434/api/generate",json={"model":"gemma3:4b","prompt":"","stream":False,"keep_alive":"5m"},timeout=180)
            response.raise_for_status()
            loaded_response = response.json()
            if not loaded_response.get("done"):
                raise RuntimeError("Preload did not complete")
            placement = httpx.get("http://127.0.0.1:11434/api/ps",timeout=10)
            placement.raise_for_status()
            placement = placement.json()
            if not any(m.get("name")=="gemma3:4b" and m.get("size_vram",0)>0 for m in placement.get("models",[])):
                raise RuntimeError("GPU model placement not confirmed")
            preload.update(status="completed",response=loaded_response,placement=placement)
        except Exception as exc:
            preload.update(status="failed",error=str(exc))
            raise
        finally:
            preload_path.write_text(json.dumps(preload,indent=2))
        result = subprocess.run(command,cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=180)
        print(result.stdout,result.stderr)
        (RESULTS/("console-"+stamp+".json")).write_text(json.dumps({"command":command,"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr},indent=2))
    except subprocess.TimeoutExpired:
        (RESULTS/("timeout-"+stamp+".json")).write_text(json.dumps({"command":command,"status":"INCONCLUSIVE","error":"180-second process deadline; pending calls are not completions"}))
        print("Stopped at process deadline; incomplete checkpoint retained.")
    except Exception as exc:
        (RESULTS/("setup-error-"+stamp+".json")).write_text(json.dumps({"status":"INCONCLUSIVE","error":str(exc)}))
        print("Setup/case failed; retained logs will be downloaded:", exc)
    finally:
        try:
            ps = httpx.get("http://127.0.0.1:11434/api/ps",timeout=5).json()
            (RESULTS/("gpu-placement-"+stamp+".json")).write_text(json.dumps(ps,indent=2))
            subprocess.run(["ollama","stop","gemma3:4b"],timeout=20,check=False)
        except Exception as exc: print("Unload/check failed:",exc)
    for path in sorted(set(RESULTS.glob("api-*.json")) - before):
        report = json.loads(path.read_text())
        row = report.get("case_result") or {}
        print(path.name,report.get("status"),report.get("error"))
        print("Case:",row.get("status"),"Synthesis exposure:",row.get("synthesis_payload_ids"))
        print("Answer:",(row.get("response") or {}).get("answer"))
    export = Path("/content")/("vaultsearch-results-"+stamp+".zip")
    with zipfile.ZipFile(export,"w",zipfile.ZIP_DEFLATED) as z:
        for p in RESULTS.rglob("*"):
            if p.is_file(): z.write(p,p.relative_to(RESULTS))
        z.write(ROOT/"BUNDLE_MANIFEST.json","BUNDLE_MANIFEST.json")
    files.download(str(export))
else:
    print("Live case disabled. Set RUN_LIVE_CASE=True to run exactly one case.")
''')
    md('## Finish\nShare the downloaded results ZIP in the chat. Disconnect and delete the Colab runtime to release its GPU when finished. Keep these checkpoints separate from Windows results. Runtime interruptions, unexposed attacks and warnings do not establish prompt-injection resistance.')
    for i,c in enumerate(cells): c['id']=f'vaultsearch-{i:02d}'
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'colab':{'name':'VaultSearch bounded security evaluation.ipynb'},'accelerator':'GPU'},'cells':cells}
    (out/'VaultSearch-Colab.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    (out/'UPLOAD_INVENTORY.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (out/'README.txt').write_text('1. In Colab choose File > Upload notebook and select VaultSearch-Colab.ipynb.\n2. Choose a GPU runtime.\n3. Run setup cells in order; upload the matching ZIP when prompted.\n4. Set RUN_LIVE_CASE=True and run just the benign case.\n5. Save and share the downloaded results ZIP.\n\nNOT uploaded or executed in Colab. Upload sends unpublished code and synthetic data to Google. No Git history, tokens, environment files, old reports, caches or model weights are bundled.\n',encoding='utf-8')
    with tempfile.TemporaryDirectory() as directory:
        extracted=Path(directory)
        with zipfile.ZipFile(bundle) as z: z.extractall(extracted)
        from redteam.api_probe import source_provenance
        assert source_provenance(extracted)['commit']==manifest['commit']
        check=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider','tests/test_api_probe.py','tests/test_presentation.py'],cwd=extracted,capture_output=True,text=True,timeout=60)
        (out/'bundle-validation.json').write_text(json.dumps({'returncode':check.returncode,'stdout':check.stdout,'stderr':check.stderr,'notebook_code_cells_ast_valid':True,'bundle_sha256':digest},indent=2),encoding='utf-8')
        print(check.stdout,check.stderr)
        if check.returncode: raise RuntimeError('Extracted-bundle regression failed')
    print(out)
    print('Bundle bytes:',bundle.stat().st_size,'Files:',len(contents))

if __name__=='__main__': main()
