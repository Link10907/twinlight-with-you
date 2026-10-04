# 生成后直接查看

默认一次请求交付两份实际结果：独立 `card/front.png` 与固定模板构建的 `site/index.html`。先完成闪卡模块，再自动构建 HTML；在当前宿主可用的图片和 HTML/Artifact 预览中打开，返回同一工件。用户不需要手写 JSON、复制内部命令或再次请求页面。保持 V10 页面与动效，不为预览重新设计界面。

Lite 资料充分时默认 `start --preview` 完成本地草稿；review 真实记录 skipped（本人未确认），保持 `draft=true`、`share_allowed=false`。真实文字确认可以在同一运行中升级，不替本人确认；Strict 继续按原来源审查与本人审阅规则执行。发布仍另需明确授权。

## 宿主检查

宿主自行检查文件、Python、图像和交互式预览能力；不让用户回答“是否能生图”。安装 skill、上传 ZIP、生成附件和执行 HTML 是不同能力。

完整运行须执行当前模式的校验、[闪卡模块](../prompts/card-generation.md) 和 [HTML 模块](../prompts/html-build.md)。将产出的 `index.html` 交给实际文件/预览工具；HTML 只消费同数据与验收素材，不重新生图、改称号、逐字重写数 MB 内嵌资源或另写 React 页面。错误在对应模块修复。

预览支持 JavaScript、data URI、Canvas/WebGL 和 requestAnimationFrame 时，检查载入、进入主星、打开卡片和返回主页；记录 WebGL 或 CSS 降级。只有源码展示或下载附件不算已运行交互预览。无浏览器工具时标视觉/交互未验证。声音可能需用户点击。

OpenAI [Work with files](https://learn.chatgpt.com/docs/artifacts-viewer) 描述 HTML 预览方式，但不保证所有 ChatGPT 网页账号具备此模板的执行能力。本项目尚未完成 ChatGPT 网页真实账号端到端测试；本地浏览器通过不能当作宿主认证。普通 ZIP 也不是已发布的 ChatGPT 插件。

## 保持交付简洁

完成消息只需：实际独立卡图与页面入口、资料范围、卡图模式、是否运行交互检查。完整 `report.html`、manifest 和详细检查留作可选附件，不让用户先读技术报告才能观看。JSON 与图层包不是有执行能力的 Agent 的最终交付。

`card/front.png` 是当前已有素材的正面合成预览，可单独由 `render-card` 复测，不调用生图、不构建页面、不烘焙动态 foil。原生清单可以包含准确程序 text；原型或 raw background/subject pair 不代表完整独立 SSR 图层已完成。正面 PNG 不能证明浏览器中的视差或 foil 已验证。

独立层可展示层内景深；只有原型的 lite 卡标静态且 depth=0。严格模式未构建独立层时，HTML 卡保留占位，另交付原型静态预览；不把静态原型称为已完成分层。无生图能力明确占位，不用作者的图替代。静态或占位降级仍自动继续 HTML，不让用户另提构建请求。

只有明确没有文件/执行工具时才给出可导入查看器的 JSON 和实际取得的图层包/原型；先说明该宿主不能保证一步完成卡片与 HTML，不声称运行了代码或完成了模板构建。单次生图或构建失败不能代替能力判断，应先自修对应模块。查看器只负责浏览器本地导入与展示，宿主 AI 的模型处理不因此变成离线。

## 本地观看无需 Node.js

`index.html` 内嵌 CSS、JavaScript、卡图、纹理和音频，现代浏览器直接打开即可；无需 Node.js、Python、npm、API Key 或服务器。复制该文件也会带走其中的个人摘要与图像，不自动公开分享。

| 操作 | 环境 |
|---|---|
| 看现成 HTML | 现代浏览器；完整卡片效果需要 WebGL |
| 生成新 HTML | Python 3.10+ 与 requirements；由宿主处理 |
| 开发时检查 JS | 可选 Node.js |
| 自动浏览器测试 | Playwright 与浏览器 |

确实有预览工具只接受 HTTP 时，宿主可在**仅包含待预览 HTML 的目录**用 Python 启动绑定 `127.0.0.1` 的临时服务；不要服务含原文和私人分析的仓库根目录。双击文件本身不需要此步骤。无法预览就提供下载与实际限制，不自动公开部署。
