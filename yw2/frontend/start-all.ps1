# start-all.ps1

Write-Host "=== 启动国家公园生态环境监测系统 ===" -ForegroundColor Green
Write-Host ""

# 设置环境变量允许所有网络访问
$env:HOST = "0.0.0.0"
$env:WDS_SOCKET_HOST = "0.0.0.0"
$env:WDS_SOCKET_PORT = 3001

# 禁用主机检查（允许所有主机访问）
$env:DANGEROUSLY_DISABLE_HOST_CHECK = "true"

Write-Host "环境变量已设置:" -ForegroundColor Yellow
Write-Host "  HOST: $env:HOST"
Write-Host "  DANGEROUSLY_DISABLE_HOST_CHECK: $env:DANGEROUSLY_DISABLE_HOST_CHECK"
Write-Host ""

# 启动 React
Write-Host "启动 React 开发服务器..." -ForegroundColor Cyan
npm start