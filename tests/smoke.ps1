# encoding: utf-8-bom
# jtool 冒烟测试（Windows）
#
# 用法: pwsh tests/smoke.ps1
#
# 覆盖：
#   1) jtool help 的退出码与输出（回归：曾落入 :cmd_use 报错并以 1 退出）
#   2) 裸调用 / 未知命令的退出码
#   3) update 复制 .bat 后使用的 CRLF 归一化表达式（内容不损坏、不写 BOM）
#   4) PowerShell 语法门：install.ps1 与 .bat 内嵌的 -Command 片段都必须能解析
#   5) 老布局 %USERPROFILE%\.devtools\jtool 的清理（删 shims/completions/repo，
#      父目录只在空时收掉——与 POSIX 的 do_uninstall 对齐，和 ptool 同规）
#
# 归一化片段与 bin/jtool.bat 的 :to_crlf 保持同步。

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$fail = 0

function Check([bool]$ok, [string]$msg) {
    if ($ok) { Write-Host "  ok   - $msg" } else { Write-Host "  FAIL - $msg"; $script:fail = 1 }
}

Write-Host "== jtool.bat help =="
$helpOut = (& "$repo\bin\jtool.bat" help 2>&1 | Out-String)
$helpRc = $LASTEXITCODE
Check ($helpRc -eq 0) "help 退出码为 0（实际 $helpRc）"
Check ($helpOut -match 'Usage:') "help 输出包含 Usage:"
Check (-not ($helpOut -match 'Error:')) "help 输出不含 Error:"

Write-Host "== 裸调用 =="
$null = (& "$repo\bin\jtool.bat" 2>&1 | Out-String)
Check ($LASTEXITCODE -eq 0) "无参数调用退出码为 0（实际 $LASTEXITCODE）"

Write-Host "== 未知命令 =="
$null = (& "$repo\bin\jtool.bat" definitely-not-a-command 2>&1 | Out-String)
Check ($LASTEXITCODE -ne 0) "未知命令退出码非 0（实际 $LASTEXITCODE）"

Write-Host "== CRLF 归一化（:to_crlf 的表达式） =="
$tmp = Join-Path $env:TEMP 'jtool-crlf-test.txt'
$utf8 = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText($tmp, "line1`nline2`n# 中文注释`n", $utf8)
$txt = [IO.File]::ReadAllText($tmp, $utf8)
$txt = $txt -replace '\r?\n', (([char]13).ToString() + ([char]10).ToString())
[IO.File]::WriteAllText($tmp, $txt, $utf8)
$bytes = [IO.File]::ReadAllBytes($tmp)
$bareLf = $false
for ($i = 0; $i -lt $bytes.Length; $i++) {
    if ($bytes[$i] -eq 10 -and ($i -eq 0 -or $bytes[$i - 1] -ne 13)) { $bareLf = $true }
}
Check (-not $bareLf) "裸 LF 已全部归一化为 CRLF"
Check (([IO.File]::ReadAllText($tmp, $utf8)) -match '# 中文注释') "中文内容未损坏"
Check ($bytes[0] -ne 0xEF) "未写入 UTF-8 BOM"
Remove-Item $tmp -ErrorAction SilentlyContinue

Write-Host "== PowerShell 语法门 =="
foreach ($f in @("$repo\installer\install.ps1")) {
    if (-not (Test-Path $f)) { Check $false "存在: $(Split-Path -Leaf $f)"; continue }
    try {
        $null = [ScriptBlock]::Create([IO.File]::ReadAllText($f))
        Check $true "可解析: $(Split-Path -Leaf $f)"
    } catch {
        Check $false "可解析: $(Split-Path -Leaf $f) -> $($_.Exception.Message)"
    }
}
$batFiles = Get-ChildItem -Path $repo -Recurse -Filter *.bat -File |
    Where-Object { $_.FullName -notmatch '\\dist\\' }
foreach ($f in $batFiles) {
    $i = 0
    foreach ($line in [IO.File]::ReadAllLines($f)) {
        $i++
        # 只认行首直接调用的 powershell -Command "..."。cmd 的
        # `for /f ... in (`powershell ...`) do ...` 里嵌的那种不是独立 payload，
        # 整行截出来的字符串本来就不可解析，必须排除（^ 锚点）。
        if ($line -match '^\s*powershell\s+[^\r\n]*-Command\s+"(.+)"\s*$') {
            $payload = $Matches[1] -replace '\\"', '"'
            try {
                $null = [ScriptBlock]::Create($payload)
                Check $true "内嵌 PS 可解析: $($f.Name):$i"
            } catch {
                Check $false "内嵌 PS 不可解析: $($f.Name):$i -> $($_.Exception.Message)"
            }
        }
    }
}

Write-Host "== 老布局 %USERPROFILE%\.devtools\jtool 的清理 =="
# 片段直接从 uninstall.bat 里取（跑的就是应用的那一行），在**假 HOME** 下验两个分支：
#   A 只剩老布局 → .devtools\jtool 与 .devtools 都收掉；
#   B 老布局 + 别的工具的数据 → 只删 jtool 那几个目录，父目录保留（只有空时才收）。
$cleanBat = Join-Path $repo 'installer\windows\uninstall.bat'
$line = $null
if (Test-Path $cleanBat) {
    $line = Select-String -Path $cleanBat -Pattern '^\s*powershell\s+[^\r\n]*-Command\s+"(.+)"\s*$' |
        Where-Object { $_.Line -match '\$root=Join-Path' } | Select-Object -First 1
}
Check ($null -ne $line) '能从 uninstall.bat 取到清理老布局的片段'
if ($null -ne $line) {
    $code = $null
    if ($line.Line -match '^\s*powershell\s+[^\r\n]*-Command\s+"(.+)"\s*$') {
        $code = $Matches[1] -replace '\\"', '"'
    }
    Check ($null -ne $code) '片段能整行截出来（应用跑的就是它）'
    if ($null -ne $code) {
        $savedHome = $env:USERPROFILE
        $fake = Join-Path $env:TEMP ('jtool-legacy-' + [IO.Path]::GetRandomFileName())
        try {
            foreach ($case in 'A', 'B') {
                $h = Join-Path $fake $case
                New-Item -ItemType Directory -Force -Path "$h\.devtools\jtool\shims", "$h\.devtools\jtool\completions", "$h\.devtools\jtool\repo" | Out-Null
                Set-Content "$h\.devtools\jtool\shims\java.bat" 'x'
                if ($case -eq 'B') {
                    New-Item -ItemType Directory -Force -Path "$h\.devtools\othertool" | Out-Null
                    Set-Content "$h\.devtools\othertool\keep.txt" 'keep'
                }
                $env:USERPROFILE = $h
                Invoke-Expression $code
                Check (-not (Test-Path "$h\.devtools\jtool")) "老布局目录已删除（场景 $case）"
                if ($case -eq 'A') {
                    Check (-not (Test-Path "$h\.devtools")) '空父目录一并收掉（场景 A）'
                } else {
                    Check (Test-Path "$h\.devtools\othertool\keep.txt") '别的工具的数据保留（场景 B）'
                }
            }
        } finally {
            $env:USERPROFILE = $savedHome
            Remove-Item -Recurse -Force $fake -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""
if ($fail -eq 0) { Write-Host "全部通过" } else { Write-Host "存在失败用例" }
exit $fail
