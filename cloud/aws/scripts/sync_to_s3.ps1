<#
.SYNOPSIS
    Sync local Lakehouse data layers (Bronze/Silver/Gold) to S3.
    Requires AWS CLI configured with a profile that has the lakehouse IAM policy.

.USAGE
    .\sync_to_s3.ps1 -Bucket "your-lakehouse-bucket" [-Profile "default"] [-DryRun]
#>

param(
    [Parameter(Mandatory=$false)] [string]$Bucket  = "1lakehousebatch",
    [Parameter(Mandatory=$false)] [string]$Profile = "default",
    [Parameter(Mandatory=$false)] [string]$Region  = "us-east-1",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Resolve project root (3 levels up from cloud/aws/scripts/)
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
$DataDir     = Join-Path $ProjectRoot "data"

$Layers = @(
    @{ Local = "bronze"; S3Prefix = "lakehouse/bronze" },
    @{ Local = "silver"; S3Prefix = "lakehouse/silver" }
)

# Gold models each go into their own sub-prefix so Athena tables don't
# overlap and pick up files from other models with different schemas.
$GoldModels = @(
    "mart_revenue_daily",
    "mart_trips_by_hour",
    "mart_trips_by_location",
    "mart_payment_breakdown"
)

foreach ($Layer in $Layers) {
    $LocalPath = Join-Path $DataDir $Layer.Local
    $S3Path    = "s3://$Bucket/$($Layer.S3Prefix)/"

    if (-not (Test-Path $LocalPath)) {
        Write-Warning "Skipping $($Layer.Local): directory not found at $LocalPath"
        continue
    }

    Write-Host "`n==> Syncing $($Layer.Local.ToUpper()) layer: $LocalPath --> $S3Path"

    $awsArgs = @(
        "s3", "sync",
        $LocalPath, $S3Path,
        "--region", $Region,
        "--profile", $Profile,
        "--exclude", "*.gitkeep"
    )
    if ($DryRun) { $awsArgs += "--dryrun" }

    & aws @awsArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "aws s3 sync failed for $($Layer.Local) layer."
        exit $LASTEXITCODE
    }
}

# Gold: copy each .parquet file into its own sub-prefix folder
Write-Host "`n==> Syncing GOLD layer (per-model sub-prefixes)..."
$GoldDir = Join-Path $DataDir "gold"
if (-not (Test-Path $GoldDir)) {
    Write-Warning "Skipping gold: directory not found at $GoldDir"
} else {
    foreach ($model in $GoldModels) {
        $LocalFile = Join-Path $GoldDir "$model.parquet"
        $S3Dest    = "s3://$Bucket/lakehouse/gold/$model/$model.parquet"

        if (-not (Test-Path $LocalFile)) {
            Write-Warning "  Skipping $model: file not found at $LocalFile"
            continue
        }

        Write-Host "    $model.parquet --> lakehouse/gold/$model/"

        $awsArgs = @(
            "s3", "cp",
            $LocalFile, $S3Dest,
            "--region", $Region,
            "--profile", $Profile
        )
        if ($DryRun) { $awsArgs += "--dryrun" }

        & aws @awsArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "aws s3 cp failed for $model."
            exit $LASTEXITCODE
        }
    }
}

Write-Host "`nAll layers synced successfully to s3://$Bucket/lakehouse/"
