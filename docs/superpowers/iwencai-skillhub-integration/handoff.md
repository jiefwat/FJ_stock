# Handoff

## 当前状态

客户端、服务端 endpoint、个股调度台、代码审查、全仓验证和本地响应式检查已完成；等待提交、合并和部署。

## 工作分支

`codex/iwencai-skillhub-integration`

## 必须保留

- stale 数据硬闸门和本地确定性结论优先。
- 外部技能 fail-open，错误不阻断个股页。
- 密钥只从服务器 `IWENCAI_API_KEY` 读取。
- 不发送持仓、成本、账号或 Cookie。
- 问财结果不自动改变仓位，不接交易执行。
