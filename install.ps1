# 一行装（PowerShell）
# 用法：irm https://raw.githubusercontent.com/<你的用户名>/arknights-story-reader/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'

$repo = 'https://github.com/Mostima1ove/arknights-story-reader'
$name = 'arknights-story-reader'
$dshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
$skills = Join-Path $dshHome 'skills'
$dest = Join-Path $skills $name

New-Item -ItemType Directory -Force -Path $skills | Out-Null

$hasGit = $null -ne (Get-Command git -ErrorAction SilentlyContinue)

if ($hasGit) {
    if (Test-Path (Join-Path $dest '.git')) {
        Write-Host "更新已有安装 ..."
        git -C $dest pull --ff-only
    } else {
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Write-Host "克隆到 $dest ..."
        git clone --depth 1 $repo $dest
    }
} else {
    Write-Host "没装 git，改用 zip 包 ..."
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("dsh-skill-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp 'pkg.zip'
    Invoke-WebRequest -Uri "$repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem $tmp -Directory | Where-Object { $_.Name -like '*main*' } | Select-Object -First 1
    if (-not $src) { $src = Get-ChildItem $tmp -Directory | Select-Object -First 1 }
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item $src.FullName $dest -Recurse
    Remove-Item $tmp -Recurse -Force
}

$py = $null
foreach ($c in @('python', 'python3', 'py')) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    $dshPy = Join-Path $dshHome 'dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
    if (Test-Path $dshPy) { $py = $dshPy }
}
if ($py) {
    Write-Host "安装依赖 pillow / numpy ..."
    & $py -m pip install --quiet pillow numpy
    & $py -c "import PIL, numpy; print('依赖 OK')"
} else {
    Write-Host "没找到 Python，请手动装：pip install pillow numpy"
}

Write-Host ""
Write-Host "装好了：$dest"
Write-Host "重启 DSH 后生效；之后说「把《活动名》的剧情做成读本」就会用它。"
