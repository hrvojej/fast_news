param(
    [string]$Path    = ".",
    [int]   $MaxItems = 50
)


function Print-LimitedTree {
    param(
        [string]$Path   = ".",
        [int]   $MaxItems = 50,
        [string]$Prefix = ""
    )
    # 1) Print the folder header
    Write-Host "$Prefix$(Split-Path $Path -Leaf)"

    # 2) Print up to $MaxItems files in this folder
    Get-ChildItem -LiteralPath $Path -File |
      Sort-Object Name |
      Select-Object -First $MaxItems |
      ForEach-Object {
        Write-Host "$Prefix|   $($_.Name)"
    }

    # 3) Recurse into each subfolder (sorted)
    Get-ChildItem -LiteralPath $Path -Directory |
      Sort-Object Name |
      ForEach-Object {
        Print-LimitedTree `
          -Path $_.FullName `
          -MaxItems $MaxItems `
          -Prefix "$Prefix|   "
    }
}

# ————————————————
# Now invoke it on your folder:
Print-LimitedTree -Path $Path -MaxItems $MaxItems
