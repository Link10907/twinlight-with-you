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

取得资源后读取本次目录中的 `AGENT.md`，使用其中的通用 `run` 控制器管理进度、续跑和验收；内部 [HTML 构建](prompts/html-build.md) 与 [闪卡生成](prompts/card-generation.md) 提示词仍独立。以本次取得的同一 revision 文件为准，不能再从 main 拼入另一版脚本。只要页面或只要闪卡时选择对应 mode；Strict 的逐句来源和本人审阅另走原工作流。

HTML 内容按 [references/lite-content.md](references/lite-content.md) 生成和校验，只使用本次资料与可见对话，不借作者或示例经历。它不要求美术设定，不调用图像工具。资料充分时先完成未确认私人草稿；当前 `run` 统一保持未确认状态，不伪造本人确认。已有确切文字批准仍有效，确需启用已确认导出时按 `AGENT.md` 使用独立构建验收。

根据 [references/platform-adapters.md](references/platform-adapters.md) 检查当前文件、执行、生图、字体和预览能力，不绑定某一平台。Lite 默认实际调用：

```bash
PY TL run <本次内容.json> --workspace <本次目录>/run --mode both
```

`PY` 是合格的实际 Python 路径，`TL` 是取得项目的 `scripts/twinlight.py` 绝对路径。保存实际返回的 `run-state.json`、`run-report.json` 和工件路径；读取 `next_action`，由 AI 执行缺少的内部动作。`needs_card` 不要求用户第二次请求。没有浏览器时使用 `--no-browser` 并说明动态未验证，不把“能创建文件”等同于站内完整观看。

闪卡按 [CARD.md](CARD.md) 单独生成和验收。生图前检查本次真实图像工具、原生透明能力和中文字体。保留返回工件、无字原型、图层与实际看图记录；代码几何形、占位或静态 SVG 不能冒充专属分层 SSR。文字仅由程序准确排版；美术保存在自己的目录，不改 HTML 内容或人物绑定。完成图层后由 AI 用同一输入、workspace 和 mode 加 `--layers <实际layers.json>` 续跑，自动接入，不等用户导入命令。两个模块各自修失败，保留已完成结果。

控制器对每次 HTML 构建执行 `verify-site`，保存 `template-receipt.json` 和实际结果；模块单独执行时同样必须运行该验收。它核对维护的模板锁并独立重组比对输出；不能在生产任务中修改或重新锁定模板来过检。文件存在、旧报告或口头声明不能替代验收，失败则修具体问题。原生层机械检查不证明绘画、原型配准或真实生图来源；浏览器报告不证明内容分析和审美。没有实际预览时说明“文件已生成，动态未验证”。

最终交付实际卡片预览与用户自己的单文件 `.html`，先给有效文件链接或附件，再打开支持的预览。JSON、命令、通用查看器、图片或源码代码块不能替代已经请求的 HTML 文件。完成消息保持简洁，实际文件、动态未验与模块未完成分别说清楚。资料不足只问必要的两三个短问题；能力缺失时交付已成功模块并说明具体缺口。当前手动查看器和未来网页服务方案不算自动路线已经完成。不会自动公开发布。
