# update-site.ps1 - Script to update site files and deploy changes

Write-Host "===== Fast News Site Update Script =====" -ForegroundColor Cyan

# Store the initial working directory for consistent relative paths
$initialPath = $pwd.Path

# Function to get content type based on file extension
function Get-ContentType {
    param (
        [string]$Extension
    )
    
    $types = @{
        # Document types
        'html' = 'text/html'
        'css'  = 'text/css'
        'js'   = 'application/javascript'
        'json' = 'application/json'
        'xml'  = 'application/xml'
        'pdf'  = 'application/pdf'
        'txt'  = 'text/plain'
        
        # Image types
        'jpg'  = 'image/jpeg'
        'jpeg' = 'image/jpeg'
        'png'  = 'image/png'
        'gif'  = 'image/gif'
        'svg'  = 'image/svg+xml'
        'ico'  = 'image/x-icon'
        'webp' = 'image/webp'
        
        # Video types
        'webm' = 'video/webm'
        'mp4'  = 'video/mp4'
        'mov'  = 'video/quicktime'
        'avi'  = 'video/x-msvideo'
        
        # Audio types
        'mp3'  = 'audio/mpeg'
        'wav'  = 'audio/wav'
        'ogg'  = 'audio/ogg'
        
        # Font types
        'woff'  = 'font/woff'
        'woff2' = 'font/woff2'
        'ttf'   = 'font/ttf'
        'otf'   = 'font/otf'
        'eot'   = 'application/vnd.ms-fontobject'
        
        # Archive types
        'zip'  = 'application/zip'
        'rar'  = 'application/x-rar-compressed'
    }
    
    if ($types.ContainsKey($Extension)) {
        return $types[$Extension]
    } else {
        return 'application/octet-stream'
    }
}

# Load or initialize the JSON cache for file hashes - Using traditional hashtable instead of PSObject
$cacheFile = Join-Path -Path $initialPath -ChildPath "fileCache.json"
$cache = @{}

# Check for PowerShell version to determine how to handle the JSON
$psVersion = $PSVersionTable.PSVersion.Major
Write-Host "PowerShell Version: $psVersion" -ForegroundColor Yellow

if (Test-Path $cacheFile) {
    try {
        Write-Host "Loading cache from $cacheFile" -ForegroundColor Yellow
        
        if ($psVersion -ge 7) {
            # PowerShell 7+ method with AsHashtable
            $cacheContent = Get-Content $cacheFile -Raw
            $cache = ConvertFrom-Json -InputObject $cacheContent -AsHashtable
            Write-Host "Cache loaded with PowerShell 7+ method" -ForegroundColor Yellow
        } else {
            # Legacy PowerShell method
            $jsonObject = Get-Content $cacheFile -Raw | ConvertFrom-Json
            $cache = @{}
            foreach ($property in $jsonObject.PSObject.Properties) {
                $cache[$property.Name] = $property.Value
            }
            Write-Host "Cache loaded with legacy PowerShell method" -ForegroundColor Yellow
        }
        
        # Show first few cache entries for debugging
        Write-Host "Current cache contains $(($cache.Keys).Count) entries" -ForegroundColor Yellow
        $i = 0
        foreach ($key in $cache.Keys) {
            if ($i -lt 5) {
                Write-Host "Cache entry: $key => $($cache[$key])" -ForegroundColor Gray
                $i++
            } else {
                break
            }
        }
    } catch {
        Write-Host "Failed to parse cache file: $_" -ForegroundColor Red
        Write-Host "Starting with an empty cache." -ForegroundColor Yellow
        $cache = @{}
    }
} else {
    Write-Host "No cache file found. Starting with an empty cache." -ForegroundColor Yellow
}

# 1. Check if we need to update the Worker code
$updateWorker = $false
$updateWorkerInput = Read-Host "Do you want to update the Worker code? (y/n)"
if ($updateWorkerInput -eq "y") {
    $updateWorker = $true
}

# 2. Upload changed files to R2
Write-Host "Checking for files to upload..." -ForegroundColor Yellow

$webPath = Join-Path -Path $initialPath -ChildPath "web"
Write-Host "Scanning for files in: $webPath" -ForegroundColor Yellow

$files = Get-ChildItem -Path $webPath -Recurse -File
Write-Host "Found $($files.Count) files to process" -ForegroundColor Yellow
$fileCount = 0
$skippedCount = 0

# Create a backup of the current cache before modifying
$originalCache = $cache.Clone()

foreach ($file in $files) {
    # Compute a consistent relative path based on the initial working directory
    $relativePath = $file.FullName.Replace("$webPath\", "").Replace("\", "/")
    $ext = $file.Extension.TrimStart('.').ToLower()
    $contentType = Get-ContentType -Extension $ext

    # Compute the file hash (using MD5)
    $currentHash = (Get-FileHash -Path $file.FullName -Algorithm MD5).Hash

    # Debug output for the first few files
    if ($fileCount -lt 5 -or $skippedCount -lt 5) {
        Write-Host "File: $relativePath" -ForegroundColor Gray
        Write-Host "  Current Hash: $currentHash" -ForegroundColor Gray
        Write-Host "  Cached Hash: $(if ($cache.ContainsKey($relativePath)) { $cache[$relativePath] } else { 'Not in cache' })" -ForegroundColor Gray
    }

    # Check if the file has changed by comparing with the cached hash
    if ($cache.ContainsKey($relativePath) -and $cache[$relativePath] -eq $currentHash) {
        $skippedCount++
        if ($skippedCount -le 5) {
            Write-Host "Skipping $relativePath (no changes detected)" -ForegroundColor Yellow
        } elseif ($skippedCount -eq 6) {
            Write-Host "Skipping more files..." -ForegroundColor Yellow
        }
        continue
    }

    # File has changed; update cache and upload
    $cache[$relativePath] = $currentHash
    $fileCount++
    Write-Host "[$fileCount/$($files.Count)] Uploading $relativePath as $contentType" -ForegroundColor Cyan

    # Store original location
    $origLocation = Get-Location
    
    # Change to fastnews directory for the wrangler command
    Set-Location (Join-Path -Path $initialPath -ChildPath "fastnews")
    
    # Build proper paths for the wrangler command
    $webFilePath = Join-Path -Path $initialPath -ChildPath "web" -AdditionalChildPath $relativePath.Replace("/", [IO.Path]::DirectorySeparatorChar)
    
    # Run the wrangler command
    wrangler r2 object put --remote "fast-news-static/$relativePath" --file $webFilePath --content-type $contentType
    
    # Return to original location
    Set-Location $origLocation
}

# Save the updated cache back to fileCache.json
$cache | ConvertTo-Json | Out-File $cacheFile -Encoding UTF8
Write-Host "Uploaded/updated $fileCount files to R2 bucket" -ForegroundColor Green
Write-Host "Skipped $skippedCount unchanged files" -ForegroundColor Green

# 3. Deploy Worker if needed
if ($updateWorker) {
    Write-Host "Deploying Worker..." -ForegroundColor Yellow
    
    # Store original location
    $origLocation = Get-Location
    
    # Change to fastnews directory for the wrangler command
    Set-Location (Join-Path -Path $initialPath -ChildPath "fastnews")
    
    # Deploy the worker
    wrangler deploy
    
    # Return to original location
    Set-Location $origLocation
    
    Write-Host "Worker deployed successfully!" -ForegroundColor Green
}

Write-Host "===== Site Update Complete =====" -ForegroundColor Cyan