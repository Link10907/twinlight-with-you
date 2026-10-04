# Twinlight · 一次生成

根据当前用户授权的资料，生成专属定义闪卡和可直接打开的 Twinlight HTML，完成后一起展示。收到本提示词或链接即开始，不让用户再分别请求两个结果。

HTML 必须由本项目已有的 Twinlight V10 固定模板实际构建，保留星系布局、双星交汇、揭卡与卡片渲染。你只填写当前用户的内容和导入完成的匹配卡包，不能自行重写、简化或用 React/Canvas/SVG 另造页面来替代。未取得完整资源或不能执行构建时，HTML 就尚未完成；继续独立卡模块并如实交付可用结果，不把自写页面称为 Twinlight 成品。

优先读取用户一次提供的完整 skill ZIP；仅有链接时，资源根为 https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/ 。由 AI 在本次允许目录取得并读取 `scripts/bootstrap.py`，用实际 Python 3.10+ 执行：已有完整项目用 `--root <项目目录>` 只读检查；资源缺失用 `--out <本次目录>/project` 取得完整资源。它解析实际 commit 后下载固定 revision，检查所需文件、运行时与依赖，不生成图像，也不自动安装依赖。链接可读不等于资源已下载或执行成功。

仅有 URL 时，可由 AI 用现有 Python 的标准库取得入口；先取得并读取脚本，再调用。以下是内部步骤，不让用户执行（路径换成实际允许目录，执行环境须满足 Python 3.10+）：

```python
from pathlib import Path; from urllib.request import urlretrieve; import subprocess, sys
p = Path("<本次目录>/bootstrap.py"); p.parent.mkdir(parents=True, exist_ok=True); urlretrieve("https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/scripts/bootstrap.py", p)
subprocess.run([sys.executable, str(p), "--out", str(p.parent / "project")], check=True)
```

取得资源后读取项目中的 [AGENT.md](https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/AGENT.md)，自动编排两份独立内部提示词：[HTML 构建](https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/prompts/html-build.md) 与 [闪卡生成](https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/prompts/card-generation.md)。以本次取得的同一 revision 文件为准；明确只要页面或只要闪卡时执行对应模块。

HTML 内容按 [references/lite-content.md](references/lite-content.md) 生成和校验，只使用本次资料与可见对话，不借作者或示例经历。它不要求美术设定，不调用图像工具。资料充分时先完成未确认的本地草稿，不伪造本人确认；实际已确认的确切文字可沿用。

闪卡按 [CARD.md](https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/CARD.md) 单独生成和验收。缺少素材时必须调用本次真实可用的图像工具，保留返回路径/工件、原型、图层与实际看图记录；代码画出的几何形、占位或静态 SVG 不能冒充专属分层 SSR。程序仅负责准确文字、边框、同像素线稿、装层和已有素材的预览。美术保存在自己的目录，不改 HTML 内容或人物绑定。两个模块各自修复失败，保留已完成结果；两者都被请求时自动导入完成且匹配的卡包，不等用户另一条命令。

每次 HTML 构建生成 `template-receipt.json`，交付前必须实际运行 `PY TL verify-site <本次site目录>`；`PY` 是实际 Python 路径，`TL` 是取得项目的 `scripts/twinlight.py` 绝对路径。此命令重新使用当前固定资源组装并比对输出 HTML。保存实际结果；资源检查、文件存在或口头声明不能替代这次验收。失败则修对应构建问题，不能宣称页面完成。原生层机械检查不能证明画得好、与原型配准或动态交互已通过；没有实际预览时明确“文件已生成，动态未验证”。

最终交付实际卡片预览与用户自己的单文件 `.html`，先给有效文件链接或附件，再打开支持的预览。JSON、命令、通用查看器、图片或源码代码块不能替代已经请求的 HTML 文件。资料不足只问必要的两三个短问题；文件/执行或生图能力缺失时如实报告具体未完成部分，不能宣称已生成完整卡片或页面。不会自动公开发布。
