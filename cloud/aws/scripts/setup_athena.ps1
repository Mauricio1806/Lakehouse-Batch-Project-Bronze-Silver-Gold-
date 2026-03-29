<#
.SYNOPSIS
    Run all Athena DDLs: create lakehouse database + 6 external tables.
    Requires AWS CLI configured with a profile that has the lakehouse IAM policy.

.USAGE
    .\setup_athena.ps1 [-Profile "default"] [-OutputBucket "aws-athena-query-results-XXXX"]

.NOTES
    Bronze table is partitioned — MSCK REPAIR TABLE is run automatically.
    Gold files are stored flat; this script also moves them into sub-prefixes
    so each Athena table maps to exactly one Parquet file.
#>

param(
    [string]$Profile      = "default",
    [string]$Region       = "us-east-1",
    [string]$Bucket       = "1lakehousebatch",
    [string]$OutputBucket = ""   # e.g. "aws-athena-query-results-123456789"
)

$ErrorActionPreference = "Stop"

# ── Resolve Athena output location ───────────────────────────────────────────
if (-not $OutputBucket) {
    $OutputBucket = $Bucket
}
$OutputLocation = "s3://$OutputBucket/athena-results/"

# Configure the workgroup so it always has an output location.
# This also makes the individual start-query-execution calls simpler
# (no --result-configuration needed, workgroup setting takes over).
Write-Host "==> Configuring Athena workgroup 'primary' output: $OutputLocation"
aws athena update-work-group `
    --work-group primary `
    --configuration-updates "ResultConfigurationUpdates={OutputLocation=$OutputLocation}" `
    --region $Region `
    --profile $Profile
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not update workgroup (may lack athena:UpdateWorkGroup permission). Will pass OutputLocation per-query instead."
    $UsePerQueryOutput = $true
} else {
    $UsePerQueryOutput = $false
}

function Invoke-Athena {
    param([string]$Query, [string]$Label)
    Write-Host "`n==> $Label"

    # Build argument list — include result-configuration only if workgroup update failed
    $startArgs = @(
        "athena", "start-query-execution",
        "--query-string", $Query,
        "--work-group", "primary",
        "--region", $Region,
        "--profile", $Profile,
        "--output", "json"
    )
    if ($UsePerQueryOutput) {
        $startArgs += "--result-configuration"
        $startArgs += "OutputLocation=$OutputLocation"
    }

    $rawResult = & aws @startArgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "start-query-execution failed [$Label]: $rawResult"
        exit 1
    }
    $result = $rawResult | ConvertFrom-Json
    $qid = $result.QueryExecutionId
    Write-Host "    QueryExecutionId: $qid"

    # Poll until terminal state
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        $status = aws athena get-query-execution `
            --query-execution-id $qid `
            --region $Region `
            --profile $Profile `
            --output json | ConvertFrom-Json
        $state = $status.QueryExecution.Status.State
        if ($state -in @("SUCCEEDED", "FAILED", "CANCELLED")) { break }
        Write-Host "    ... $state"
    }

    if ($state -ne "SUCCEEDED") {
        $reason = $status.QueryExecution.Status.StateChangeReason
        Write-Error "Query FAILED [$Label]: $reason"
        exit 1
    }
    Write-Host "    SUCCEEDED"
}

# ── Step 0: Reorganise flat Gold files into sub-prefixes ──────────────────────
$GoldModels = @(
    "mart_revenue_daily",
    "mart_trips_by_hour",
    "mart_trips_by_location",
    "mart_payment_breakdown"
)

Write-Host "`n==> Reorganising Gold Parquet files into sub-prefixes..."

foreach ($model in $GoldModels) {
    $src = "s3://$Bucket/lakehouse/gold/$model.parquet"
    $dst = "s3://$Bucket/lakehouse/gold/$model/$model.parquet"

    $exists = aws s3 ls $src --profile $Profile --region $Region 2>&1

    if (($LASTEXITCODE -eq 0) -and ($exists -match $model)) {
        Write-Host "    Moving $model.parquet -> $model/$model.parquet"
        aws s3 mv $src $dst --profile $Profile --region $Region
    }
    else {
        Write-Host "    $model already in sub-prefix or not found - skipping mv"
    }
}
# ── Step 1: Database ──────────────────────────────────────────────────────────
Invoke-Athena "CREATE DATABASE IF NOT EXISTS lakehouse" "Create database: lakehouse"

# ── Step 2: Bronze table (partitioned) ───────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$AthenaDir = Resolve-Path (Join-Path $ScriptDir "../athena")

$bronzeSQL = (Get-Content (Join-Path $AthenaDir "create_bronze_table.sql") -Raw) `
    -replace "--.*`n", ""   # strip single-line comments
Invoke-Athena $bronzeSQL "Create table: lakehouse.bronze_trips"

# ── Step 3: MSCK REPAIR on Bronze ────────────────────────────────────────────
Invoke-Athena "MSCK REPAIR TABLE lakehouse.bronze_trips" "Repair partitions: bronze_trips"

# ── Step 4: Silver table ──────────────────────────────────────────────────────
$silverSQL = (Get-Content (Join-Path $AthenaDir "create_silver_table.sql") -Raw) `
    -replace "--.*`n", ""
Invoke-Athena $silverSQL "Create table: lakehouse.silver_trips"

# ── Step 5: Gold tables ───────────────────────────────────────────────────────
$goldFiles = @(
    @{ File = "create_gold_table.sql";                      Label = "Create table: lakehouse.mart_revenue_daily"     },
    @{ File = "create_gold_trips_by_hour_table.sql";        Label = "Create table: lakehouse.mart_trips_by_hour"     },
    @{ File = "create_gold_trips_by_location_table.sql";    Label = "Create table: lakehouse.mart_trips_by_location" },
    @{ File = "create_gold_payment_breakdown_table.sql";    Label = "Create table: lakehouse.mart_payment_breakdown" }
)

foreach ($g in $goldFiles) {
    $sql = (Get-Content (Join-Path $AthenaDir $g.File) -Raw)
    $sql = $sql -replace "--.*`n", ""
    Invoke-Athena $sql $g.Label
}

Write-Host "`nAll Athena tables created successfully."
Write-Host "Database 'lakehouse' is now queryable in Athena (region: $Region)."
Write-Host ""
Write-Host "Sample queries:"
Write-Host "  SELECT * FROM lakehouse.mart_revenue_daily ORDER BY trip_date DESC LIMIT 10;"
Write-Host "  SELECT * FROM lakehouse.mart_trips_by_hour ORDER BY hour_of_day;"
Write-Host "  SELECT * FROM lakehouse.mart_payment_breakdown ORDER BY total_trips DESC;"
Write-Host "  SELECT * FROM lakehouse.mart_trips_by_location ORDER BY total_trips DESC LIMIT 25;"
