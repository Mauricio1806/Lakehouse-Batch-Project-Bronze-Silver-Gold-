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
    @{ Local = "silver"; S3Prefix = "lakehouse/silver" },
    @{ Local = "gold";   S3Prefix = "lakehouse/gold"   }
)

$DryRunFlag = if ($DryRun) { "--dryrun" } else { "" }

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

Write-Host "`nAll layers synced successfully to s3://$Bucket/lakehouse/"
