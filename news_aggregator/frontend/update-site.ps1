# update-site.ps1 - Script to update site files and deploy changes using rclone

Write-Host "===== Fast News Site Update Script =====" -ForegroundColor Cyan

# Store the initial working directory for consistent relative paths
$initialPath = $pwd.Path

# Function to get content type based on file extension (preserved for potential future use)
function Get-ContentType {
    param (
        [string]$Extension
    )
    
    $types = @{
        'html' = 'text/html'
        'css'  = 'text/css'
        'js'   = 'application/javascript'
        'json' = 'application/json'
        'xml'  = 'application/xml'
        'pdf'  = 'application/pdf'
        'txt'  = 'text/plain'
        'jpg'  = 'image/jpeg'
        'jpeg' = 'image/jpeg'
        'png'  = 'image/png'
        'gif'  = 'image/gif'
        'svg'  = 'image/svg+xml'
        'ico'  = 'image/x-icon'
        'webp' = 'image/webp'
        'webm' = 'video/webm'
        'mp4'  = 'video/mp4'
        'mov'  = 'video/quicktime'
        'avi'  = 'video/x-msvideo'
        'mp3'  = 'audio/mpeg'
        'wav'  = 'audio/wav'
        'ogg'  = 'audio/ogg'
        'woff'  = 'font/woff'
        'woff2' = 'font/woff2'
        'ttf'   = 'font/ttf'
        'otf'   = 'font/otf'
        'eot'   = 'application/vnd.ms-fontobject'
        'zip'   = 'application/zip'
        'rar'   = 'application/x-rar-compressed'
    }
    
    if ($types.ContainsKey($Extension)) {
        return $types[$Extension]
    } else {
        return 'application/octet-stream'
    }
}

# 1. Check if we need to update the Worker code
$updateWorker = $true


# 2. Upload changed files to R2 using rclone
Write-Host "Starting rclone sync to upload new or updated files..." -ForegroundColor Yellow

# Get the web folder path
$webPath = Join-Path -Path $initialPath -ChildPath "web"

# Use the full path to rclone.exe to ensure it is found.
$rcPath = "C:\rclone\rclone.exe"
Write-Host "Running command: `"$rcPath`" sync `"$webPath`" fn:fast-news-static" -ForegroundColor Gray

# Execute the rclone sync command. (Make sure 'fn' is configured correctly via rclone config.)
& $rcPath sync $webPath "fn:fast-news-static"

# 3. Deploy Worker if needed
if ($updateWorker) {
    Write-Host "Deploying Worker..." -ForegroundColor Yellow

    # Change to fastnews directory for the wrangler command
    Set-Location (Join-Path -Path $initialPath -ChildPath "fastnews")

    # Deploy the worker using wrangler
    wrangler deploy

    # Return to original location
    Set-Location $initialPath

    Write-Host "Worker deployed successfully!" -ForegroundColor Green
}

Write-Host "===== Site Update Complete =====" -ForegroundColor Cyan
