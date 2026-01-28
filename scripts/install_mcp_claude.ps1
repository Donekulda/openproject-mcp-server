# install_mcp.ps1
# Automatic installation script for OpenProject MCP for Claude Desktop
# Instructions: Right-click -> Run with PowerShell

$ErrorActionPreference = "Stop"

Write-Host ">>> Starting OpenProject MCP installation..." -ForegroundColor Cyan

# 1. Determine project path
$ScriptPath = $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path (Split-Path $ScriptPath -Parent) -Parent
Write-Host "📂 Project directory: $ProjectRoot"

# 2. Check Python Virtual Environment (.venv)
$VenvPython = "$ProjectRoot\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Virtual environment (.venv) not found. Attempting to create new one..." -ForegroundColor Yellow
    # Check if 'uv' is available
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        Write-Host "Running 'uv sync'..."
        Set-Location $ProjectRoot
        uv sync
    } else {
        Write-Error "Please install 'uv' or run setup manually before running this script."
        Pause
        Exit
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Error "Still cannot find python in .venv. Installation failed."
    Pause
    Exit
}

# 3. Collect information from user
Write-Host "`n🔐 Configure OpenProject connection" -ForegroundColor Cyan
$OpenProjectUrl = Read-Host "Enter OpenProject URL (e.g., https://company.openproject.com)"
if ([string]::IsNullOrWhiteSpace($OpenProjectUrl)) {
    Write-Error "URL cannot be empty."
    Exit
}

$ApiKey = Read-Host "Enter your API Key (Get it from My Account > Access Tokens)"
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Error "API Key cannot be empty."
    Exit
}

# 4. Update Claude Desktop Config
$ConfigFile = "$env:APPDATA\Claude\claude_desktop_config.json"
$ConfigDir = Split-Path $ConfigFile -Parent

if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
}

$ConfigJson = @{}
if (Test-Path $ConfigFile) {
    try {
        $Content = Get-Content $ConfigFile -Raw -Encoding UTF8
        $ConfigJson = $Content | ConvertFrom-Json -Depth 10 # Depth to avoid flattening object
    } catch {
        Write-Host "⚠️ Config file is corrupted or empty, will create new one." -ForegroundColor Yellow
    }
}

# Ensure object structure
if (-not $ConfigJson.PSObject.Properties["mcpServers"]) {
    $ConfigJson = $ConfigJson | Select-Object *, @{mcpServers = @{}}
}

# Create configuration for this Server
$ServerConfig = @{
    command = $VenvPython
    args    = @("$ProjectRoot\openproject-mcp-fastmcp.py")
    env     = @{
        PYTHONPATH          = $ProjectRoot
        OPENPROJECT_URL     = $OpenProjectUrl
        OPENPROJECT_API_KEY = $ApiKey
    }
}

# Add/Update to config
$ConfigJson.mcpServers | Add-Member -Type NoteProperty -Name "openproject-fastmcp" -Value $ServerConfig -Force

# Save file
$ConfigJson | ConvertTo-Json -Depth 10 | Set-Content $ConfigFile -Encoding UTF8

Write-Host "`n✅ INSTALLATION SUCCESSFUL!" -ForegroundColor Green
Write-Host "Updated config file at: $ConfigFile"
Write-Host "👉 Please restart Claude Desktop to start using."
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
