# Handoff

## 当前状态

客户端、服务端 endpoint、个股调度台、代码审查、全仓验证、本地响应式检查和公网部署均已完成。

公网入口：`https://stock.jiewat-kaka-fj.com/`

服务器已通过权限受限的环境文件配置 `IWENCAI_API_KEY`，真实问财财务质量查询和生产登录态 endpoint 均已验收通过。

## 工作分支

`main`

## 部署记录

- 首次部署提交：`98787b57d43d125626331b60d7d63491432eef96`。
- 真实网关兼容提交：`c72f70d176f8a489e220878356ae1540a5ae9d48`。
- 服务器目录：`/opt/stock-ts`，分支 `main`，tracked worktree 干净。
- 回滚包：`/opt/stock-ts/.deploy_backups/iwencai-20260714-153500-a6a1f05/source-a6a1f05.tar.gz`。
- 兼容修复回滚包：`/opt/stock-ts/.deploy_backups/iwencai-status-fix-20260714-155431/source-before.tar.gz`。
- `stock-ts.service`、`stock-ts-signal-desk.service` 和 Nginx 均为 `active`。
- 公网 `/healthz` 返回 HTTP 200；根路径保持登录跳转；匿名研究请求返回 HTTP 401。

## 密钥维护

1. 密钥只保存在服务器 `/opt/stock-ts/.env`，文件权限保持 `600`，不要写入仓库、页面或日志。
2. 由于密钥曾通过聊天传递，建议在问财后台轮换；轮换后重启 `stock-ts.service` 并复跑登录态查询。
3. systemd drop-in `/etc/systemd/system/stock-ts.service.d/iwencai.conf` 只记录环境文件路径，不包含密钥值。

## 必须保留

- stale 数据硬闸门和本地确定性结论优先。
- 外部技能 fail-open，错误不阻断个股页。
- 密钥只从服务器 `IWENCAI_API_KEY` 读取。
- 不发送持仓、成本、账号或 Cookie。
- 问财结果不自动改变仓位，不接交易执行。
