# Aster Market 运维入口

## 本地启动

```bash
make install
make test
ASTER_SNAPSHOT_PATH=data/market_snapshot.json make run
```

默认监听 `127.0.0.1:8501`。可通过 `HOST`、`PORT` 和 `ASTER_SNAPSHOT_PATH` 覆盖。
行情文件不会打包进仓库，也不会在缺失时由程序生成示例价格。

## 健康检查

```bash
curl -fsS http://127.0.0.1:8501/healthz
curl -fsS http://127.0.0.1:8501/api/snapshot
```

`/healthz` 只证明进程可响应；`/api/snapshot` 的 `status=ready` 才证明行情文件可解析。

## 部署约束

- 发布目录统一使用 `/opt/aster-market`，禁止覆盖式修改其他应用目录。
- 进程仅绑定回环地址，由既有公网代理转发；应用本身没有登录和会话。
- 部署只替换 Aster 主服务，不修改反向代理、旁路服务、定时器或行情原文件。
- 运行时行情复制到 `/opt/aster-market/data/market_snapshot.json`，原始文件保持不变。
- 每次发布先验证测试、静态检查和本地 HTTP，再原子切换服务目录。

## 回滚

保留上一版发布目录和服务单元备份。回滚只切回上一版 Aster 目录，不从其他分支拷贝旧产品代码。
