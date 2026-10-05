# Twinlight · 一次生成

根据当前用户授权资料，一次生成专属定义闪卡和可直接打开的 Twinlight HTML，完成后一起展示。默认 both；明确只要 HTML 或卡片时仅做相应模块。不让用户重复请求、不要求用户选择美术参数。

## 取得完整且固定版本的项目

优先使用用户提供的完整 skill ZIP。只有链接时，资源根为 `https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/`。由 AI 在允许目录下载并先读取 `scripts/bootstrap.py`，再用实际 Python 3.10+ 执行 `--out <本次目录>/project`；已有完整项目执行 `--root <项目目录>`。bootstrap 解析 commit、下载固定 revision、检查依赖与模板锁，不生图、不自动安装依赖。后续只使用取得的同一 revision，不从 main 混入另一版文件。

内部取得入口示例（替换为实际允许目录，不让用户执行）：

```python
from pathlib import Path
from urllib.request import urlretrieve
p = Path("<本次目录>/bootstrap.py")
p.parent.mkdir(parents=True, exist_ok=True)
urlretrieve("https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/scripts/bootstrap.py", p)
# Read the downloaded script before executing it.
```

资源与执行能力缺失时说明具体缺口；读取 URL 不等于完成构建。不得以自写 React/Canvas/SVG 页面替代项目 HTML。

## 执行

读本地 `AGENT.md`，以同一输入和 workspace 调用 public `run`，执行实际 `next_action` 后续跑。美术使用 `references/quality-workflow.md`，HTML 使用 `prompts/html-build.md`；只在需要的阶段读取其细节。

绘画顺序为：当前偏好与否决项 → 具体画面方案 → 真实无字原型与评审 → 原生层与无字合成评审 → 独立排字与最终视差/闪光评审。选定原型不合格就不进入分层。旧素材复用必须明确标注，不能算本次新生图。没有工具时保留成功模块，不用几何占位冒充绘画。

以 `run-report.json` / `delivery-report.json` 的实际 `complete` 和 `outputs` 为交付依据。待验卡在 `candidate_outputs` 中，不能称完整闪卡，也不自动接入最终 HTML。固定模板必须通过 `verify-site`，浏览器未运行则动态未验证；禁止修改模板锁或伪写检查状态来凑完成。

只用本次授权资料；署名为实际总结者。私人草稿不要求二次确认，仍保持未确认、不可自动公开。先展示真实卡片预览与个人 HTML 文件链接，再给必要的简短限制；不能用口头“完成”、JSON、截图或文件存在代替实际验收。
