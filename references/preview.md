# 生成后直接查看

默认交付顺序是：生成实际 HTML → 在宿主支持的交互式预览中打开 → 返回可下载的同一文件。用户无需看命令、手写 JSON 或搭建前端工程。

## 网页 AI 与 Agent

1. 检查本次聊天是否实际具备文件读取、Python 执行和 HTML/Artifact 预览。上传 ZIP、安装 skill、生成附件和渲染页面是不同能力，分别报告。
2. 完整运行必须执行原有校验器与固定模板构建。把构建产出的 `index.html` 交给宿主的文件/预览工具。使用现成文件加载能力，避免让模型将数 MB 的内嵌素材逐字重写进聊天；不为预览临时改写成另一个 React 页面。
3. 宿主确实提供 HTML、Canvas 或 Artifact 执行预览时优先使用；只有 Markdown/源码展示不算完成交互渲染。检查页面已加载、主星可进入、卡片可打开，说明 WebGL 完整运行还是 CSS 降级。若没有浏览器检查工具，标注视觉/交互尚未验证。
4. 预览需要由 JavaScript、图片 data URI、Canvas/WebGL 和 requestAnimationFrame 支持。沙箱可能禁用某些能力；声音可能需要用户点击后播放。宿主无法渲染时，返回下载文件和限制，不自动公开部署。
5. 如果只有聊天写作能力，交付带原话的分析审查稿。即使 AI 能另写一个漂亮网页，也不能称为运行了本项目的校验与固定模板。

截至 2026-10-03，OpenAI 的 [Work with files](https://learn.chatgpt.com/docs/artifacts-viewer) 明确描述了支持 HTML 预览的界面和生成文件的查看方式，但没有保证所有 ChatGPT 网页账号都能执行这个模板。此项目尚未完成 ChatGPT 网页端的真实账号端到端测试；本地浏览器通过不能当作网页宿主认证。普通 ZIP 附件也不是已经发布的 ChatGPT 原生插件。

## 本地观看不需要 Node.js

生成的 `index.html` 内嵌 CSS、JavaScript、纹理、卡图和音频，可直接用现代浏览器打开；复制这一文件即可移动页面。观看不需要 Python、Node.js、npm、API Key 或本地服务器。分享该文件仍会分享它包含的摘要和图像。

| 操作 | 所需环境 |
|---|---|
| 看已经生成好的 HTML | 现代浏览器；完整卡片效果需要 WebGL |
| 用原有脚本生成新的 HTML | Python 3.10+、requirements.txt；可由 AI 宿主执行 |
| 开发时检查 JavaScript 语法 | 可选 Node.js，用于 node --check |
| 自动浏览器回归测试 | 开发依赖 Playwright 与浏览器 |

若某个预览工具只接受 HTTP 地址，有 Python 时可由宿主在**仅包含待预览页面的目录**运行 `python -m http.server 8000 --bind 127.0.0.1 --directory outputs/preview`，再打开 `http://127.0.0.1:8000/`。命令路径需按实际工作目录调整。不要把包含真实历史的仓库根目录作为服务根；直接双击文件本身不需要这一步。
