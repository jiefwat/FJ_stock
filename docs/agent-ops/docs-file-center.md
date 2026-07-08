# Docs 文件中台

`docs.jiewat-kaka-fj.com` 使用独立的文件中台管理通用 HTML、报告和资料，不混入 `stock.jiewat-kaka-fj.com` 或 `dsa.jiewat-kaka-fj.com`。

## 访问边界

- 管理台：`https://docs.jiewat-kaka-fj.com/file-center/`
- 上传后的公开文件：`https://docs.jiewat-kaka-fj.com/files/<group>/<filename>`
- 管理台和 API 由 Nginx Basic Auth 保护。
- 公开文件继承 docs 站点的 `X-Robots-Tag: noindex, nofollow`。

## 服务组成

- 应用脚本：`scripts/docs_file_center_app.py`
- 服务器应用路径：`/opt/jiewat-docs/app/docs_file_center_app.py`
- 静态文件根目录：`/opt/jiewat-docs/public`
- 文件实体目录：`/opt/jiewat-docs/public/files`
- 索引文件：`/opt/jiewat-docs/data/manifest.json`
- 本地监听：`127.0.0.1:8721`

## 能力

- 新建文件夹分组。
- 上传文件时选择目标分组。
- 添加外部 URL 链接时选择目标分组。
- 页面卡片可拖拽到其他分组。
- 文件和链接也可通过列表上的分组下拉框移动。
- 支持复制公开链接。
- 打开文件中台时会自动扫描 `/opt/jiewat-docs/public`，把手动发布到根目录或子目录、但未写入索引的静态文件补到目录里。
- 根目录文件会显示在系统分组“站点根目录”。

## 安全约束

- 不允许把上传 API 裸露到公网无鉴权访问。
- 上传类型只允许常见静态文件和资料格式。
- 单个文件默认限制为 50MB。
- 不要上传凭证、Webhook、私有持仓、服务器 Key 或内部地址。
