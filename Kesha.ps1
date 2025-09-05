# Simple PowerShell script to launch gui.py from same directory

$scriptDir = $PSScriptRoot
$guiPath = Join-Path $scriptDir "gui.py"

# Change to the script directory (same as gui.py)
Set-Location $scriptDir

# Try different Python commands
$pythonCommands = @("python", "py", "python3")
$success = $false

foreach ($cmd in $pythonCommands) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        try {
            Write-Host "Starting gui.py with $cmd..." -ForegroundColor Green
            & $cmd $guiPath
            $success = $true
            break
        }
        catch {
            Write-Host "Failed with $cmd, trying next..." -ForegroundColor Yellow
        }
    }
}

if (-not $success) {
    Write-Host "Could not start gui.py. Make sure Python is installed." -ForegroundColor Red
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
