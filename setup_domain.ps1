# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script needs to be run as Administrator. Please right-click and select 'Run as Administrator'."
    Exit
}

$hostsFile = "$env:SystemRoot\System32\drivers\etc\hosts"
$domainName = "devops.internal.eapmanager"
$ipAddress = "10.0.0.98"

# Check if entry already exists
$hostsContent = Get-Content $hostsFile
$entryExists = $hostsContent | Where-Object { $_ -match "^[^#]*$domainName" }

if ($entryExists) {
    Write-Host "Domain entry already exists in hosts file."
} else {
    # Add new entry
    $newEntry = "`n$ipAddress`t$domainName"
    Add-Content -Path $hostsFile -Value $newEntry
    Write-Host "Domain entry added successfully!"
}

Write-Host "`nSetup complete! You can now access your application at:"
Write-Host "http://$domainName`:5000"
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
