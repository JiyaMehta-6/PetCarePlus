<#>
.SYNOPSIS
    PetCare+ Windows Setup — one-command bootstrap for the entire stack.

.DESCRIPTION
    Creates a virtual environment, installs Python dependencies, downloads
    the embedding model (BGE-small-en-v1.5) and generation model
    (Qwen2.5-1.5B-Instruct), builds the knowledge base + FAISS index,
    and verifies the installation.

.NOTES
    - Requires: Windows 10/11, PowerShell 5.1+, Python 3.10+, Git
    - All large assets go to D:\projects\petCareplus (configurable via $ProjectRoot)
    - Set $SkipLLM = $true to skip generation model download (retrieval-only mode)
    - Run from the repository root (where this script lives)
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$ProjectRoot = (Split-Path -Parent $MyInvocation.MyCommand.Definition),

    [Parameter()]
    [switch]$SkipLLM,

    [Parameter()]
    [switch]$SkipKBBuild,

    [Parameter()]
    [switch]$ForceReinstall
)

# --- Colors & helpers --------------------------------------------------------
$Green  = [ConsoleColor]::Green
$Yellow = [ConsoleColor]::Yellow
$Red    = [ConsoleColor]::Red
$Cyan   = [ConsoleColor]::Cyan
$Gray   = [ConsoleColor]::Gray

function Write-Header { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor $Cyan }
function Write-Ok     { param($msg) Write-Host "  ✓ $msg" -ForegroundColor $Green }
function Write-Warn   { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor $Yellow }
function Write-Err    { param($msg) Write-Host "  ✗ $msg" -ForegroundColor $Red }
function Write-Info   { param($msg) Write-Host "  → $msg" -ForegroundColor $Gray }

# --- Sanity checks -----------------------------------------------------------
Write-Header "PetCare+ Setup"

if (-not (Test-Path "$ProjectRoot\requirements.txt")) {
    Write-Err "requirements.txt not found — run this script from the repo root."
    exit 1
}

$python = "python"
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
    Write-Err "Python not found in PATH. Install Python 3.10+ from https://python.org"
    exit 1
}

$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVer -lt [version]"3.10") {
    Write-Err "Python 3.10+ required (found $pyVer)."
    exit 1
}
Write-Ok "Python $pyVer detected"

# --- Virtual environment -----------------------------------------------------
$venvDir = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvDir -and $ForceReinstall) {
    Write-Warn "Removing existing .venv (--ForceReinstall)"
    Remove-Item $venvDir -Recurse -Force
}

if (-not (Test-Path $venvDir)) {
    Write-Header "Creating virtual environment"
    python -m venv ".venv" | Out-Null
    Write-Ok "Virtual environment created"
} else {
    Write-Ok "Virtual environment exists"
}

$pip = Join-Path $venvDir "Scripts\pip.exe"
$py   = Join-Path $venvDir "Scripts\python.exe"

# --- Upgrade pip/setuptools/wheel -------------------------------------------
Write-Header "Upgrading pip, setuptools, wheel"
& $pip install --upgrade pip setuptools wheel -q
Write-Ok "Build tools upgraded"

# --- Install Python dependencies --------------------------------------------
Write-Header "Installing Python dependencies"
$req = Join-Path $ProjectRoot "requirements.txt"
& $pip install -r $req -q
Write-Ok "Requirements installed"

# Install CPU torch explicitly (requirements.txt has torch==2.13.0+cpu but index URL may be needed)
Write-Info "Ensuring CPU torch wheel..."
& $pip install "torch==2.13.0+cpu" --index-url https://download.pytorch.org/whl/cpu -q
Write-Ok "Torch (CPU) ready"

# --- Configure HF caches to project root --------------------------------------
$hfHome   = Join-Path $ProjectRoot "huggingface"
$torchHome= Join-Path $ProjectRoot "torch"
$modelsDir = Join-Path $ProjectRoot "models"
$knowledgeDir = Join-Path $ProjectRoot "knowledge"
[Environment]::SetEnvironmentVariable("HF_HOME", $hfHome, "Process")
[Environment]::SetEnvironmentVariable("TORCH_HOME", $torchHome, "Process")
New-Item -ItemType Directory -Path $hfHome, $torchHome, $modelsDir, $knowledgeDir -Force | Out-Null
Write-Ok "HF/Torch caches → $hfHome"
Write-Ok "Models → $modelsDir"
Write-Ok "Knowledge → $knowledgeDir"

# --- Download embedding model ------------------------------------------------
Write-Header "Downloading embedding model (BGE-small-en-v1.5 ~380 MB)"
$embDir = Join-Path $modelsDir "embeddings\bge-small-en-v1.5"
if (-not (Test-Path "$embDir\config.json")) {
    Write-Info "Downloading — this may take a few minutes..."
    & $py -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'BAAI/bge-small-en-v1.5',
    local_dir=r'$embDir',
    local_dir_use_symlinks=False,
    resume_download=True
)
"
    Write-Ok "Embedding model ready at $embDir"
} else {
    Write-Ok "Embedding model already present"
}

# --- Download generation model ----------------------------------------------
if (-not $SkipLLM) {
    Write-Header "Downloading generation model (Qwen2.5-1.5B-Instruct ~1.2 GB)"
    $llmDir = Join-Path $modelsDir "llm\qwen"
    if (-not (Test-Path "$llmDir\config.json")) {
        Write-Info "Downloading — this may take several minutes..."
        & $py -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'Qwen/Qwen2.5-1.5B-Instruct',
    local_dir=r'$llmDir',
    local_dir_use_symlinks=False,
    resume_download=True
)
"
        Write-Ok "Generation model ready at $llmDir"
    } else {
        Write-Ok "Generation model already present"
    }
} else {
    Write-Warn "Skipping LLM download (--SkipLLM). App will run in retrieval-only mode."
}

# --- Build Knowledge Base ----------------------------------------------------
if (-not $SkipKBBuild) {
    Write-Header "Building knowledge base + FAISS index (3,751 chunks)"
    $env:PYTHONPATH = $ProjectRoot
    $kbStart = Get-Date
    & $py "developer/build_kb.py"
    $kbDur = (Get-Date) - $kbStart
    Write-Ok "KB built in $($kbDur.TotalMinutes.ToString('F1')) min — 3,751 chunks indexed"
} else {
    Write-Warn "Skipping KB build (--SkipKBBuild)"
}

# --- Verify installation -----------------------------------------------------
Write-Header "Verifying installation"
$env:PYTHONPATH = $ProjectRoot
try {
    & $py -c "
from app.rag.retrieval import Retriever
from app.rag.query_understanding import understand
r = Retriever()
ctx = understand('test query for indie dog')
chunks, conf = r.retrieve(ctx, final_k=3)
print(f'Retriever OK — {len(chunks)} chunks, confidence={conf:.3f}')
"
    Write-Ok "Retrieval pipeline functional"
} catch {
    Write-Err "Retriever test failed: $($_.Exception.Message)"
    exit 1
}

# --- Final summary -----------------------------------------------------------
Write-Header "Setup Complete 🎉"
Write-Host @"
PetCare+ is ready. Next steps:

  1. Launch the app:
       .\run_petcare.bat

  2. Or run evaluation:
       \$env:PYTHONPATH = '$ProjectRoot'
       .venv\Scripts\python.exe evaluation/evaluate.py

  3. Or run unit tests:
       .venv\Scripts\python.exe -m pytest tests -q

Project root: $ProjectRoot
Models:       $modelsDir
Knowledge:    $knowledgeDir
Data:         $(Join-Path $ProjectRoot 'data')
Logs:         $(Join-Path $ProjectRoot 'logs')
"@