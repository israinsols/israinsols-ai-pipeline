# One-time Windows service setup for Israinsols Pipeline
# Run this once as Administrator.

$projectPath = 'C:\Users\ccslaptophyd\OneDrive\Desktop\israinsols_pipeline'
$pythonPath = Join-Path $projectPath 'venv\Scripts\python.exe'
$redisExe = 'C:\Program Files\Redis\redis-server.exe'
$redisConf = 'C:\Program Files\Redis\redis.windows-service.conf'
$redisService = 'IsrainsolsRedis'
$workerService = 'IsrainsolsCeleryWorker'
$beatService = 'IsrainsolsCeleryBeat'

Write-Host "Project path: $projectPath"
Write-Host "Python path: $pythonPath"
Write-Host "Redis executable: $redisExe"

function Install-RedisService {
    if (Get-Service -Name $redisService -ErrorAction SilentlyContinue) {
        Write-Host "Redis service '$redisService' already exists."
        return
    }

    if (-Not (Test-Path $redisExe)) {
        Write-Error "Redis executable not found at $redisExe"
        return
    }

    & $redisExe --service-install $redisConf --loglevel verbose
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Redis service '$redisService' installed successfully."
        sc.exe config $redisService start= auto | Out-Null
    } else {
        Write-Error "Failed to install Redis service. Exit code: $LASTEXITCODE"
    }
}

function Create-ServiceWithNssm {
    param(
        [string]$serviceName,
        [string]$appPath,
        [string]$appArgs
    )

    $nssm = Get-Command nssm -ErrorAction SilentlyContinue
    if (-Not $nssm) {
        Write-Error "NSSM is not installed or not in PATH. Install NSSM first and run this script again."
        return $false
    }

    if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
        Write-Host "Service '$serviceName' already exists."
        return $true
    }

    & $nssm install $serviceName $appPath $appArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create service '$serviceName' with NSSM."
        return $false
    }
    & $nssm set $serviceName AppDirectory $projectPath
    & $nssm set $serviceName Start SERVICE_AUTO_START
    Write-Host "Service '$serviceName' created successfully."
    return $true
}

function Install-CeleryServices {
    if (-Not (Test-Path $pythonPath)) {
        Write-Error "Python environment not found at $pythonPath"
        return
    }

    $workerArgs = '-m celery -A config.celery worker --loglevel=info --concurrency=2 --pool=solo'
    $beatArgs = '-m celery -A config.celery beat --loglevel=info'

    Create-ServiceWithNssm -serviceName $workerService -appPath $pythonPath -appArgs $workerArgs | Out-Null
    Create-ServiceWithNssm -serviceName $beatService -appPath $pythonPath -appArgs $beatArgs | Out-Null
}

function Start-Services {
    Get-Service -Name $redisService -ErrorAction SilentlyContinue | Where-Object { $_.Status -ne 'Running' } | Start-Service
    Get-Service -Name $workerService -ErrorAction SilentlyContinue | Where-Object { $_.Status -ne 'Running' } | Start-Service
    Get-Service -Name $beatService -ErrorAction SilentlyContinue | Where-Object { $_.Status -ne 'Running' } | Start-Service

    Write-Host "Services started:"
    Get-Service -Name $redisService,$workerService,$beatService | Format-Table Name, Status
}

Install-RedisService
Install-CeleryServices
Start-Services
