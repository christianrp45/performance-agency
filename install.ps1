# Copia as skills da agência para ~/.claude/skills (substitui versões anteriores destas skills).
$ErrorActionPreference = "Stop"
$origem = Join-Path $PSScriptRoot "skills"
$destino = Join-Path $HOME ".claude\skills"
New-Item -ItemType Directory -Force $destino | Out-Null
Get-ChildItem $origem -Directory | ForEach-Object {
    $alvo = Join-Path $destino $_.Name
    if (Test-Path $alvo) { Remove-Item $alvo -Recurse -Force }
    Copy-Item $_.FullName $alvo -Recurse
    Write-Host "instalada: $($_.Name)"
}
$registro = Join-Path $HOME ".claude\agencia\clientes.md"
if (-not (Test-Path $registro)) {
    New-Item -ItemType Directory -Force (Split-Path $registro) | Out-Null
    "# Clientes da agência`n`n| Cliente | Pasta |`n|---|---|`n" | Out-File $registro -Encoding utf8
    Write-Host "criado: $registro"
}
