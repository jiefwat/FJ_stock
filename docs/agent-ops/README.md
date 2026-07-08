# Agent Ops

## 冷启动步骤

1. 确认 `AGENTS.md` 的项目约定。
2. 查看 `docs/agent-ops/agent-handoff-current.md` 理解当前本地路径、服务器路径、数据源、持仓和下一步任务。
3. 查看 `docs/architecture/README.md` 理解边界。
4. 查看 `docs/tech-specs/README.md` 理解技术决策。
5. 查看 `docs/TODO.md` 获取当前任务。
6. 需求协作时只读取 `docs/superpowers/README.md` 登记的活跃需求。

## 网页发布与生成

- 生成、改造或发布公开网页时，先阅读 `docs/agent-ops/web-page-generation-guide.md`。
- `jiewat-kaka-fj.com` 是默认域名族；独立应用优先使用子域名，例如 `stock.jiewat-kaka-fj.com`。
- 公网页面默认开启只读与安全边界，不暴露凭证、Webhook、私有持仓或后台写操作。

## 验证命令

```bash
make lint
make test
```
