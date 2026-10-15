param([int]$Port=8013, [string]$Origin='http://127.0.0.1:3013', [string]$DatabaseName='phase3-browser')
$ErrorActionPreference='Stop'
if ($DatabaseName -notmatch '^[a-z0-9-]+$') { throw 'Use a simple test database name.' }
$backend = Join-Path $PSScriptRoot '../backend'
$backend = (Resolve-Path -LiteralPath $backend).Path
$testDirectory = Join-Path $backend '.test-data'
New-Item -ItemType Directory -Path $testDirectory -Force | Out-Null
$database = Join-Path $testDirectory "$DatabaseName.sqlite"
$env:ENVIRONMENT='test'
$env:ALLOW_TEST_SQLITE='true'
$env:DATABASE_URL='sqlite:///'+$database.Replace('\','/')
$env:AUTH_SECRET=[Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:COOKIE_SECURE='false'
$env:CORS_ORIGINS=ConvertTo-Json -Compress -InputObject @($Origin,'http://localhost:3000','http://127.0.0.1:3000')
Push-Location $backend
try {
 & '.\.venv\Scripts\python.exe' -m alembic upgrade head
 if ($LASTEXITCODE -ne 0) { throw 'Test migration failed.' }
 & '.\.venv\Scripts\python.exe' -m alembic current
 & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
