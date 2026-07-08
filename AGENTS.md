# AGENTS.md

## 项目约定

- 项目名：`stock-ts`
- 包名：`stock_ts`
- 治理等级：`standard`
- 项目类型：`mixed`
- 服务标识：`stock-ts`

## 冷启动入口

1. 阅读 `docs/agent-ops/README.md`
2. 阅读 `docs/architecture/README.md`
3. 阅读 `docs/tech-specs/README.md`
4. 查看 `docs/TODO.md`
5. 如涉及需求协作，进入 `docs/superpowers/README.md`

## 常用命令

```bash
make install
make lint
make test
make run
```

## 协作约束

- 不提交真实凭证、内部地址或线上配置。
- 修改运行入口、配置、日志或外部依赖时，同步更新 docs 与测试。
- 企业部署相关路径默认围绕 `app_id` 收敛。
