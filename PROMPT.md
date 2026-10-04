# Twinlight · 一次生成

根据当前用户授权的资料，生成专属定义闪卡和可直接打开的 Twinlight HTML，完成后一起展示。收到本提示词或链接即开始，不让用户再分别请求两个结果。

取得完整项目资源：https://github.com/Link10907/twinlight-with-you ，资源根为 https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/ 。读取 [AGENT.md](AGENT.md) 自动编排两份独立内部提示词：[HTML 构建](prompts/html-build.md) 与 [闪卡生成](prompts/card-generation.md)。明确只要页面或只要闪卡时，执行对应模块。

HTML 内容按 [references/lite-content.md](references/lite-content.md) 生成和校验，只使用本次资料与可见对话，不借作者或示例经历。它不要求美术设定，不调用图像工具。资料充分时先完成未确认的本地草稿，不伪造本人确认；实际已确认的确切文字可沿用。

闪卡按 [CARD.md](CARD.md) 单独生成和验收；美术设置、原型、图层和预览保存在自己的目录，不改 HTML 内容或人物绑定。两个模块各自修复失败，保留已完成结果。两者都被请求时，自动将完成且绑定匹配的卡包导入页面，不等待用户另一条命令。

最终交付实际卡片预览与用户自己的单文件 `.html`，先给有效文件链接或附件，再打开支持的预览。JSON、命令、通用查看器、图片或源码代码块不能替代已经请求的 HTML 文件。资料不足只问必要的两三个短问题；文件/执行或生图能力缺失时如实报告具体未完成部分，不能宣称已生成完整卡片或页面。不会自动公开发布。
