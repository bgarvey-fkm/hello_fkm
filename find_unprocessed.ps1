# Find 20 unprocessed loans
$allInputs = Get-ChildItem -Path "loan_files_inputs" -Filter "loan_*_tree.json" | 
    ForEach-Object { $_.Name -replace 'loan_(\d+)_tree\.json', '$1' } | 
    Sort-Object

$unprocessed = @()

foreach ($loanId in $allInputs) {
    $summaryPath = "loan_docs\$loanId\income_analysis\consistency_summary_*.json"
    if (!(Test-Path $summaryPath)) {
        $unprocessed += $loanId
    }
    if ($unprocessed.Count -ge 20) {
        break
    }
}

Write-Host "Found $($unprocessed.Count) unprocessed loans:"
$unprocessed -join ' '
