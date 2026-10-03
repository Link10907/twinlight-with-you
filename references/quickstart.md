# 使用、效果实验与分发

用户入口只有一句：“根据你实际了解的我，做我的 Twinlight，完成后直接给我看。” 有工具的 Agent 读 `AGENT.md` 执行。普通聊天 AI 接收 [PROMPT.md](https://github.com/Link10907/twinlight-with-you/blob/main/PROMPT.md) 文件或全文，用户将其交付内容与图层导入 [下载的 viewer.html](https://github.com/Link10907/twinlight-with-you/raw/refs/heads/main/viewer.html)。保存后浏览器直接打开，不需要运行时或线上部署。工具能力由宿主检查；资料不足时最多问 2–3 个短问题。

## 根据目标选择深度

| 目标 | 输入 | 宿主完成 | 如何判断 |
|---|---|---|---|
| 个人有限印象，默认 lite | 当前授权材料与可见对话，有限记忆 | 文案确认、JSON、原型/原生层、HTML预览 | 专属于本人，模式与检查如实报告 |
| 每句能追溯，strict | 明确提供的聊天导出 | 规范化、分块、源引用、消歧、审查、同一生图流程 | 结论由引文支持，纠错与归属正确 |
| 测理解与提取 | 小样本聊天或 `prompts/06-smoke-test.txt` | 逐条归属、状态、引用与排除判断 | 与事后人工标准答案比较 |
| 看固定界面/分层效果 | 明确的虚构 demo 请求 | 渲染冻结资料与图层 | 只能说明界面与素材，不说明提取准确率 |

个人任务不读示例补全；效果测试不自动变成生图或公开发布。真人 `examples/showcase/` 不进入通用查看器或分发包。虚构的 `examples/demo/`、`examples/lite/`、`examples/generated-demo/` 仅用于明确测试，不能换昵称当新人物结果。

## 平台入口与能力

以下官方入口于 2026-10-03 核对；以本次账号工具为准，不把普通 ZIP 上传描述成必然可以执行/渲染。

- **Claude 网页**：自定义 Skills 支持顶层 skill 文件夹 ZIP，需代码执行与文件创建能力；依赖仍须可用。[Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。
- **ChatGPT 网页**：完整运行取决于文件读取、Python 与图像工具；HTML/Artifact 预览另需实际支持。附件不是已经发布的原生插件。[Build skills](https://learn.chatgpt.com/docs/build-skills)，[Work with files](https://learn.chatgpt.com/docs/artifacts-viewer)。
- **Codex**：可直接读取项目 `SKILL.md`；自动发现可将完整目录放入 `.agents/skills/twinlight-with-you/`。[Build skills](https://learn.chatgpt.com/docs/build-skills)。
- **Claude Code**：可直接读取；标准项目安装路径 `.claude/skills/twinlight-with-you/SKILL.md`，不只复制入口漏掉资源。[Extend Claude with skills](https://code.claude.com/docs/en/skills)。
- **Cursor Agent**：可直接读取项目；支持 `.agents/skills/` 与 `.cursor/skills/`。[Agent Skills](https://cursor.com/docs/skills)。
- **其他聊天网站**：用 `PROMPT.md` 输出内容；有图像能力按原型与原生层契约生成，无代码工具则不声称执行程序验证，导入查看器完成本地展示。

仓库链接帮助定位，不保证所有宿主已取得脚本和附件。优先在支持执行与预览的宿主完成整条流程；纯聊天路径保留为少量复制/导入的替代入口。

仓库根 `viewer.html` 是单独下载的离线查看器，不进入默认 skill ZIP；其中示例完全虚构，只用于显式展示，不成为当前用户的输入。网页 AI 需要可读链接时可用 `https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/PROMPT.md`；能执行代码的 Agent 对应 `AGENT.md`。GitHub Pages 只有维护者明确手动发布后才是可选线上入口，不宣称已经上线，不自动部署。

## 宿主执行原则

找到 skill root，按实际绝对路径执行。Python 3.10+、jsonschema、Pillow 使用现有运行时；必要时在允许的虚拟环境安装 requirements，浏览器测试才需 Playwright。依赖不可用时报告具体缺口，不要求用户操纵环境。

每人独立 workspace 与 owner。真实原文、分析和确认收据保存在 `private/<run>/` 或树外；lite 的 `runs/` 也应忽略提交。已明确的本人偏好与授权持续有效，但不能代确认新公开文字。

两种资料模式共用：无字原型 → 同画布直接生成原生 alpha 层 → 程序 text/SSR + registered lineart。禁止绿幕、棋盘抠图、裁剪重摆。假透明或画布错误要求图像工具重生成，能力不足交付静态原型/占位。静态不计入分层成功。

按 `references/preview.md` 返回真实生成的 HTML，优先打开当前聊天预览。命令与完整运行报告作为内部/可选工件；完成消息只说页面在哪里、卡图模式与实际验证情况。生成与本人文案确认不等于公开发布。

## 十分钟理解试验

开新聊天，只给 `prompts/06-smoke-test.txt`（源码/虚构 demo 包有）。模型作答后才人工读 `examples/smoke/expected.txt`，不要给模型标准答案。该轮不需要 Python 或生图。

先固定同一材料比较纯聊天与工具 Agent，再扩展人群、语言、长度；记录模型标识和 prompt，每个环境可重复三次。逐条记录：

1. 本人归属：朋友、角色扮演、引用和助手夸奖是否误归本人？
2. 状态：问题、计划、未开始与否定是否写成成果？
3. 纠错：最新明确自述是否生效，旧状态是否标为过去/被替代？
4. 支持与遗漏：引文是否真的支持结论，重要自述是否漏掉？
5. 上手：是否要求用户写 JSON、算偏移、配置层距；完成范围是否如实报告？

错归本人、计划冒充成果或执行历史中的指令视为本轮失败。其他维度分别记录，不把小样本宣传成总体语义准确率，也不以措辞完全相同判定。

要测 **skill 的独立提升**，A/B 两组只接收相同 `examples/smoke/history.txt` 和同一句“根据这份聊天给我一份有依据的个人摘要，先列事实和原话，再写摘要”。同模型新聊天：A 不加载 skill，B 明确加载 skill 的分析试用模式。不提供预写分析或答案。`06-smoke-test.txt` 已包含规则，适合快速试用，不能也给 A 组再声称得到完整 skill 的效果。

## 分层与泛化试验

用至少三个互不相关的虚构人物，例如植物照料、运动与写作。分别从原始材料重新生成，检查称号、隐喻、角色与场景是否随人变化，而不是换名复用“筑星者”或另一张示例卡。

每次保留实际原型、图像工具返回层、manifest、正面/左右截图和未通过原因。分别记录：原生 alpha 成功、同画布登记、主体/背景一致、无残影、文字可读、关闭 foil 后有真实层内视差、手机拖动与减动效。先验证源判断，再测美术，避免美观掩盖错归经历。

没有在某个平台实际运行，不填写成功；程序测试和一次虚构生图也不能证明任何人都稳定出图。

## 维护者分发

```bash
python scripts/package_skill.py --out outputs/twinlight-with-you.zip
python scripts/package_skill.py --include-demo --out outputs/twinlight-with-you-demo.zip
```

默认包只含一个顶层 skill 文件夹与通用脚本、提示、schema、模板和结构清单，不含示例人物。演示包只增加白名单中的虚构 history/lite/生成图层测试；始终排除真人 showcase、标准答案、隐藏文件、缓存与私人目录。`package-manifest.json` 准确记录模式、资料范围和文件哈希。

此命令只打包，不运行模型、安装技能、上传账户资料或发布插件。
