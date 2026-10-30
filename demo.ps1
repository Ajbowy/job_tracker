<#
Demo PowerShell script for job_tracker.
Runs: add -> list -> update -> list -> stats -> backup -> delete -> final list
Outputs are saved to files in the same folder and opened in Notepad for easy viewing.
#>

# Ensure script runs from its own folder (so relative paths work)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Host "Running demo in: $scriptDir"

Write-Host "1) Add a demo job"
python .\job_tracker.py add --company "DemoCo" --position "Intern" --date 2025-10-29 --status applied --notes "Demo job" > add_output.txt 2>&1
Get-Content .\add_output.txt | Write-Host

Write-Host "2) List after add (sorted by date desc)"
python .\job_tracker.py list --sort date --desc > list_after_add.txt 2>&1
Get-Content .\list_after_add.txt | Write-Host

# find the id of the last job (last CSV row's first column)
$last = Get-Content .\jobs.csv | Select-Object -Last 1
if (-not $last) {
    Write-Host "Could not read jobs.csv or it's empty."; exit 1
}
$lastId = ($last -split ',')[0]
Write-Host "Found last job id: $lastId"

Write-Host "3) Update the demo job"
python .\job_tracker.py update $lastId --status interview --notes "Demo updated" > update_output.txt 2>&1
Get-Content .\update_output.txt | Write-Host

Write-Host "4) List after update"
python .\job_tracker.py list --sort id > list_after_update.txt 2>&1
Get-Content .\list_after_update.txt | Write-Host

Write-Host "5) Stats"
python .\job_tracker.py stats > stats_output.txt 2>&1
Get-Content .\stats_output.txt | Write-Host

Write-Host "6) Backup CSV"
python .\job_tracker.py backup --out .\demo_backup.csv > backup_output.txt 2>&1
Get-Content .\backup_output.txt | Write-Host

Write-Host "7) Delete the demo job"
python .\job_tracker.py delete $lastId --yes > delete_output.txt 2>&1
Get-Content .\delete_output.txt | Write-Host

Write-Host "8) Final list"
python .\job_tracker.py list --sort id > final_list.txt 2>&1
Get-Content .\final_list.txt | Write-Host

Write-Host "Demo finished. Output files: add_output.txt, list_after_add.txt, update_output.txt, list_after_update.txt, stats_output.txt, backup_output.txt, delete_output.txt, final_list.txt, demo_backup.csv"

# Optionally open the main outputs in Notepad for convenience (uncomment if you want)
# notepad .\list_after_add.txt
# notepad .\list_after_update.txt
# notepad .\stats_output.txt
# notepad .\final_list.txt
