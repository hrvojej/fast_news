# Save this as delete-r2-objects-v2.ps1

# Your Cloudflare account ID (from the error message)
$accountId = "4e5d50e5c54202502e8b325e64584fae"
$bucketName = "fnews"

# You'll need to get an API token from Cloudflare dashboard with R2 permissions
$apiToken = Read-Host -Prompt "Enter your Cloudflare API token"

# First, list all objects in the bucket
$headers = @{
    "Authorization" = "Bearer $apiToken"
    "Content-Type" = "application/json"
}

# Get a list of all objects
$listUrl = "https://api.cloudflare.com/client/v4/accounts/$accountId/r2/buckets/$bucketName/objects"
$response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers

# Check if we got a valid response
if ($response.success -eq $true -and $response.result.objects.Count -gt 0) {
    Write-Host "Found $($response.result.objects.Count) objects to delete"
    
    # Delete each object
    foreach ($object in $response.result.objects) {
        $objectKey = [System.Web.HttpUtility]::UrlEncode($object.key)
        Write-Host "Deleting object: $($object.key)"
        
        $deleteUrl = "https://api.cloudflare.com/client/v4/accounts/$accountId/r2/buckets/$bucketName/objects/$objectKey"
        try {
            Invoke-RestMethod -Uri $deleteUrl -Method DELETE -Headers $headers
            Write-Host "  Deleted successfully" -ForegroundColor Green
        } catch {
            Write-Host "  Failed to delete: $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "No objects found or error in listing objects" -ForegroundColor Yellow
}

# After all objects are deleted, delete the bucket
Write-Host "Attempting to delete bucket: $bucketName"
$deleteBucketUrl = "https://api.cloudflare.com/client/v4/accounts/$accountId/r2/buckets/$bucketName"
try {
    Invoke-RestMethod -Uri $deleteBucketUrl -Method DELETE -Headers $headers
    Write-Host "Bucket deleted successfully!" -ForegroundColor Green
} catch {
    Write-Host "Failed to delete bucket: $_" -ForegroundColor Red
}