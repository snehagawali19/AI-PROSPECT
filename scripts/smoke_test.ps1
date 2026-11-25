# Smoke test a running instance (Windows PowerShell). Usage: .\scripts\smoke_test.ps1 [-Base http://localhost:4000]
param([string]$Base = "http://localhost:4000")
$pass = 0; $fail = 0
function Check($name, $expected, $method, $path, $body = $null) {
    try {
        $params = @{ Uri = "$Base$path"; Method = $method; UseBasicParsing = $true; ErrorAction = "Stop" }
        if ($body) { $params.Body = $body; $params.ContentType = "application/json" }
        $code = (Invoke-WebRequest @params).StatusCode
    } catch {
        $code = [int]$_.Exception.Response.StatusCode
    }
    if ($code -eq $expected) { Write-Host "PASS  $name ($code)"; $script:pass++ }
    else { Write-Host "FAIL  $name (got $code, expected $expected)"; $script:fail++ }
}
Check "health"             200 GET  "/health"
Check "openapi docs"       200 GET  "/docs"
Check "openapi schema"     200 GET  "/openapi.json"
Check "validation error"   422 POST "/prospect-discovery" '{"query":"a"}'
Check "missing body field" 422 POST "/prospect-discovery" '{}'
Write-Host "--- live discovery (needs real keys in .env; 503 = LLM keys/model IDs not configured) ---"
Check "live discovery"     200 POST "/prospect-discovery" '{"query":"Restaurant owners in Dubai UAE"}'
Write-Host "passed=$pass failed=$fail"
if ($fail -gt 0) { exit 1 }
