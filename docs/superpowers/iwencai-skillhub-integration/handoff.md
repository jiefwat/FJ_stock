# Handoff

## 当前状态

客户端、服务端 endpoint、个股调度台、代码审查、全仓验证、本地响应式检查和公网部署均已完成。

公网入口：`https://stock.jiewat-kaka-fj.com/`

服务器尚未配置 `IWENCAI_API_KEY`，因此页面会安全显示“未配置”，StockTs 本地个股分析保持可用；真实问财查询需补 Key 后验收。

## 工作分支

`main`

## 部署记录

- 首次部署提交：`98787b57d43d125626331b60d7d63491432eef96`。
- 服务器目录：`/opt/stock-ts`，分支 `main`，tracked worktree 干净。
- 回滚包：`/opt/stock-ts/.deploy_backups/iwencai-20260714-153500-a6a1f05/source-a6a1f05.tar.gz`。
- `stock-ts.service`、`stock-ts-signal-desk.service` 和 Nginx 均为 `active`。
- 公网 `/healthz` 返回 HTTP 200；根路径保持登录跳转；匿名研究请求返回 HTTP 401。

## 后续启用真实问财

1. 仅在服务器安全配置 `IWENCAI_API_KEY`，不要写入仓库、页面或日志。
2. 重启 `stock-ts.service`，确认 `/healthz` 仍返回 `ok`。
3. 使用登录账号执行一次真实问财查询，验证技能路由、来源标签和无 Key 回显。

## 必须保留

- stale 数据硬闸门和本地确定性结论优先。
- 外部技能 fail-open，错误不阻断个股页。
- 密钥只从服务器 `IWENCAI_API_KEY` 读取。
- 不发送持仓、成本、账号或 Cookie。
- 问财结果不自动改变仓位，不接交易执行。
