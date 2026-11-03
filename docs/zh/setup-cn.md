# 本地开发环境启动指南（前后端）

本文记录 Windows（PowerShell）下一键之外的手动启动配置。官方脚本 `scripts/dev-local.sh`
依赖 bash + tmux + lsof，在 Windows 上不可用；以下配置与其等价，实测可用。

## 总览

| 服务 | 端口 | 入口 |
|---|---|---|
| 后端 FastAPI | 18790 | `http://localhost:18790/app`（控制台）· `/docs`（API 文档）· `/login`（登录） |
| 前端 Vite | 5173 | 仅 HMR 用；浏览器访问走后端 18790 |

`TREG_FRONTEND_DEV=true` 时后端会代理 Vite 的 HMR——修改 `.vue` / i18n 文件即时热更新。

## 后端 FastAPI

### 启动命令

在仓库根目录 `d:/projects/github/treg` 执行：

```powershell
.venv\Scripts\python.exe -m treg --reload
```

> **坑：不要用 `uv run python -m treg`。** `uv run` 会触发依赖同步，`quickjs`
> v1.19.4 的 C 扩展在本机编译失败（`-Werror=incompatible-pointer-types`）。
> 必须直接使用已装好的 `.venv`。

### 环境变量

启动前需在同一 shell 中设置（子进程继承环境）：

| 变量 | 值 | 说明 |
|---|---|---|
| `TREG_SECRET_KEY` | 来自 `scripts/.dev-home/dev-keys.env` | Fernet 加密密钥，复用可保证重启后密文可解 |
| `TREG_SESSION_SECRET` | 来自同上 | 会话签名密钥 |
| `TREG_EMAIL_DEV_MODE` | `true` | OTP 验证码直接显示在登录页 / API 响应里，无需邮件服务 |
| `TREG_FRONTEND_DEV` | `true` | 后端代理 Vite HMR |
| `TREG_PUBLIC_URL` | `http://localhost:18790` | |
| `TREG_CONNECT_DEMO_ENABLED` | `true` | |
| `TREG_DATABASE_URL` | `sqlite+aiosqlite:///d:/projects/github/treg/treg-dev.db` | 独立开发库，不碰真实数据 |

### dev-keys

`scripts/.dev-home/dev-keys.env`（`KEY=VALUE` 格式）保存稳定的开发专用密钥，
缺失时每个 `--reload` 重启都会丢失会话与已存密文。生成方式（与
`scripts/dev-local.sh` 的 `ensure_dev_keys` 等价）：

```powershell
$keys = "TREG_SECRET_KEY=" + (uv run python -m treg keygen)
$bytes = New-Object byte[] 24; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$keys += "`nTREG_SESSION_SECRET=" + (($bytes | ForEach-Object { $_.ToString('x2') }) -join '')
Set-Content -Path scripts/.dev-home/dev-keys.env -Value $keys
```

### 可复制的完整启动脚本

```powershell
cd d:/projects/github/treg
# 1) 注入 dev-keys
Get-Content scripts/.dev-home/dev-keys.env | ForEach-Object {
  $p = $_ -split '=',2
  if ($p.Count -eq 2) { Set-Item -Path "env:$($p[0].Trim())" -Value $p[1].Trim() }
}
# 2) 开发环境变量
$env:TREG_EMAIL_DEV_MODE      = 'true'
$env:TREG_FRONTEND_DEV        = 'true'
$env:TREG_PUBLIC_URL          = 'http://localhost:18790'
$env:TREG_CONNECT_DEMO_ENABLED= 'true'
$env:TREG_DATABASE_URL        = 'sqlite+aiosqlite:///d:/projects/github/treg/treg-dev.db'
# 3) 后台启动（日志重定向到仓库根目录）
Start-Process -FilePath "d:/projects/github/treg/.venv/Scripts/python.exe" `
  -ArgumentList "-m","treg","--reload" `
  -WorkingDirectory "d:/projects/github/treg" `
  -RedirectStandardOutput "d:/projects/github/treg/.dev-backend.out" `
  -RedirectStandardError  "d:/projects/github/treg/.dev-backend.err" `
  -WindowStyle Hidden
```

日志：仓库根目录 `.dev-backend.out` / `.dev-backend.err`。

## 前端 Vite

```powershell
cd d:\projects\github\treg\frontend
npm run dev -- --host localhost
```

前置条件：

- `frontend/node_modules` 存在（首次执行 `npm ci --include=dev`）
- `predev` 钩子会自动构建 agent-setup 运行时（`vite build -c vite.agent-setup.config.ts`）
- Node >= 22.12

后台启动（日志重定向）：

```powershell
Start-Process -FilePath "cmd.exe" `
  -ArgumentList "/c","npm run dev -- --host localhost" `
  -WorkingDirectory "d:/projects/github/treg/frontend" `
  -RedirectStandardOutput "d:/projects/github/treg/.dev-frontend.out" `
  -RedirectStandardError  "d:/projects/github/treg/.dev-frontend.err" `
  -WindowStyle Hidden
```

日志：仓库根目录 `.dev-frontend.out` / `.dev-frontend.err`。

## 停止服务

### 常规停止

杀掉两类进程：

1. `python -m treg` 的 reloader 父进程与 worker（命令行含 `-m treg --reload`）
2. 前端的 node 进程（监听 5173）

```powershell
Get-CimInstance Win32_Process -Filter "Name like 'python%'"
  | Where-Object { $_.CommandLine -match '-m treg' }
  | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-NetTCPConnection -LocalPort 5173 -State Listen
  | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### ⚠️ 停止时的孤儿 worker 坑点

`--reload` 模式下 uvicorn 用 multiprocessing 派生 worker。**只杀 reloader 父进程
不够**：worker 会变成孤儿并继续持有继承来的监听 socket——此时
`Get-NetTCPConnection` 显示监听者仍是已死的父 PID，HTTP 依然可达，端口看似
被"幽灵进程"占用。

必须把 multiprocessing-fork 子进程一并终止（特征：命令行含
`spawn_main(parent_pid=<已死PID>)`）：

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'"
  | Where-Object { $_.CommandLine -match 'spawn_main' }
  | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

之后 18790 / 5173 端口才真正释放。

## 其他

- 独立开发 CLI（不碰 `~/.treg/config.json`）需要 bash 环境，见
  `scripts/dev-local.sh cli <args>`；Windows 下可手动设置
  `HOME=scripts/.dev-home` 并在其 `.treg/config.json` 写入
  `{"base_url":"http://localhost:18790"}` 后运行 `.venv\Scripts\treg.exe`。
- 数据库 schema 由 alembic 管理，后端启动时自动 `upgrade head`。
- 官方一键脚本（macOS/Linux）：`scripts/dev-local.sh up|down|status|logs|reset`。
