# 使用、效果实验与分发

一句话入口见 `README.md`：默认由 `PROMPT.md` / `AGENT.md` 在同一次请求中调用独立 HTML 与闪卡模块，各自修复，完成匹配卡包后自动接入最终 HTML。用户明确只要其中一个时才执行单独模块。默认不使用旧的串行状态机把两者成功与失败绑在一起；导入只消费完成且绑定匹配的卡包。

## 根据目标选择深度

| 目标 | 输入 | 宿主完成 | 如何判断 |
|---|---|---|---|
| 个人有限印象，默认 lite | 当前授权材料与可见对话，有限记忆 | 默认未确认私人草稿、固定模板 HTML、独立卡包与预览 | HTML 模板来源已验收；卡片文件、艺术与动态实际完成范围分别报告 |
| 每句能追溯，strict | 明确提供的聊天导出 | 规范化、分块、源引用、消歧、审查与 HTML 构建 | 结论由引文支持，纠错与归属正确 |
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
- **其他聊天网站**：按实际工具执行对应模块；只有聊天/生图工具时不能声称完成 HTML 构建。手动查看器导入由用户明确选择，最终仍下载个人 HTML。

最稳入口是同一次消息提供启动语和完整 skill ZIP。仅有 URL 时，AI 需实际下载/文件/执行能力；从 raw `PROMPT.md` 取得编排，按其 bootstrap 步骤下载完整资源，不能只读提示词就写替代网页。链接不等于工具或资源已齐全，不自动改变交付目标。

仓库根 `viewer.html` 是单独下载的离线查看器，不进入默认 skill ZIP；其中示例完全虚构，只用于显式展示，不成为当前用户的输入。网页 AI 需要可读链接时可用 `https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/PROMPT.md`；能执行代码的 Agent 对应 `AGENT.md`。GitHub Pages 只有维护者明确手动发布后才是可选线上入口，不宣称已经上线，不自动部署。

## 宿主执行原则

找到 skill root，按实际绝对路径执行。先用 `scripts/bootstrap.py --root <已有root>` 检查完整资源与实际运行时；缺资源时由 AI 下载并读取 bootstrap，再用 `--out <新目录>` 解析 main 的实际 commit 并取得该 revision 的完整 archive，可用 `--revision <40位SHA>` 固定已知版本。后续使用同一资源目录。bootstrap 不自动安装依赖或生图；Python 3.10+、jsonschema、Pillow 使用现有运行时，必要时由 AI 在允许的环境安装 requirements 后重查，浏览器测试才需 Playwright。具体能力仍不可用时如实报告，不要求用户操纵环境。

每次 HTML 构建生成 `template-receipt.json`，交付前实际运行 `twinlight.py verify-site <site目录>`，重新从当前固定资源组装并比对 HTML。未执行或失败不能宣称固定页面完成，也不能改写简化版；保留已通过的基础页面和独立卡片。来源比对只验文件，动态交互另需实际运行。卡片必须使用真实图像工具或已授权同主人素材，不能以代码几何形、占位或 SVG 冒充专属绘画；保留实际工具返回、原型、各层和视觉/互动记录。

每人独立 workspace 与 owner。真实原文、分析和确认收据保存在 `private/<run>/` 或树外；lite 的 `runs/` 也应忽略提交。已明确的本人偏好与授权持续有效，但不能代确认新公开文字。

闪卡流程的原型、原生层、排字、线稿与有限修复统一见 `CARD.md` 和美术契约。HTML 不接管这些操作，只消费已完成的匹配卡包。

按 `references/preview.md` 返回真实生成且已验模板来源的 HTML，优先打开当前聊天预览。命令与完整运行报告作为内部/可选工件；完成消息只说页面在哪里、卡图模式与实际验证情况。卡片文件完成但缺实际互动检查时明确“文件已生成，动态未验证”；静态/占位则明确分层卡未完成。生成与本人文案确认不等于公开发布。

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

完整新生成实验见 [fresh-generation-eval.md](fresh-generation-eval.md)。从新原始材料开始，不提供预写 JSON、分析、原型或图层；分别验收资源取得、内容、固定 HTML、真实生图、层配准和实际动态，再检查一次请求自动接入。已有 JSON 加已有原生层的正向试验只证明构建/导入/预览路径，不能替代新内容与新绘画测试。

## 维护者分发

```bash
python scripts/package_skill.py --out outputs/twinlight-with-you.zip
python scripts/package_skill.py --include-demo --out outputs/twinlight-with-you-demo.zip
```

默认包只含一个顶层 skill 文件夹与通用脚本、提示、schema、模板和结构清单，不含示例人物。演示包只增加白名单中的虚构 history/lite/生成图层测试；始终排除真人 showcase、标准答案、隐藏文件、缓存与私人目录。`package-manifest.json` 准确记录模式、资料范围和文件哈希。

此命令只打包，不运行模型、安装技能、上传账户资料或发布插件。
