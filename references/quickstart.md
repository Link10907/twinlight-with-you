# 直接交给 AI 的使用与效果测试

用户只需提供历史材料、表达目标、审查结果。脚本命令、证据定位、JSON 和阶段工件由宿主处理。

## 先选一个实际目标

| 目标 | 材料 | AI 要做的事 | 完成标志 |
|---|---|---|---|
| 测理解与提取 | `prompts/06-smoke-test.txt` 或一段有消息边界的聊天 | 逐条归属、状态、引用与排除判断；写有限范围摘要 | 带原话的判断与摘要，标注未运行程序验证 |
| 测固定页面 | 源码或单独 demo 包内的虚构资料 | 运行 demo，预览并返回 HTML | 固定页面能打开；不能据此评价提取 |
| 用自己的历史生成草稿 | 完整 skill 包与明确提供的原始历史 | 环境检查、规范化、逐块提取、消歧、verify/review/build | 实际生成的审查稿、HTML、工件与验证结果 |

默认不把效果测试升级为生图或公开发布。完整人物分层卡按原工作流继续，只调用实际可用且获授权的图像工具。

## 平台入口

以下入口于 2026-10-03 核对，功能与权限仍以实际账号为准。

- **Claude 网页**：原生自定义 Skills 支持包含 skill 文件夹的 ZIP，在 Customize > Skills 上传，并启用代码执行与文件创建。官方说明：[Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。本项目依赖仍需在执行环境中可用；安装成功不等于已经验证完整流水线。
- **ChatGPT 网页**：可以先将自包含的小样本文本作为任务材料。完整 ZIP 工作流取决于当前聊天能否读取文件、执行 Python 和取得所需依赖。不要把普通附件上传描述成原生 skill 安装。官方文档区分本地独立 skills 与通过插件分发到网页的 skills：[Build skills](https://learn.chatgpt.com/docs/build-skills)。本 ZIP 是 skill 文件夹包，没有声明已发布成 ChatGPT 插件。
- **Codex**：在项目里直接要求读取根 `SKILL.md`，即可显式执行，无需先安装。若希望自动发现，将完整 skill 文件夹放入 `.agents/skills/twinlight-with-you/`，保留相对目录结构。官方说明：[Build skills](https://learn.chatgpt.com/docs/build-skills)。
- **Claude Code**：可以直接读取项目 `SKILL.md`；安装后的标准项目路径为 `.claude/skills/twinlight-with-you/SKILL.md`。不要只复制入口文件而漏掉脚本和模板。官方说明：[Extend Claude with skills](https://code.claude.com/docs/en/skills)。
- **Cursor Agent**：可以直接读取项目 `SKILL.md`；项目 skills 支持 `.agents/skills/` 和 `.cursor/skills/`。官方说明：[Agent Skills](https://cursor.com/docs/skills)。网页/云端 Agent 的本地文件可见性另有边界。
- **其他 AI 网站**：先用小样本测试。只有实际具备读取资源、运行代码和返回文件的工具链时，才尝试完整编译。仅能聊天的模型可以给出分析审查稿。

仓库链接可以帮助定位项目，但不能保证宿主已取得所有脚本、模板和附件；完整包比只给链接更可靠。

## 有工具的宿主如何执行

1. 找到实际包含 `SKILL.md` 的目录，记为 skill root。所有脚本路径相对它解析；所有输入输出路径使用实际工作目录。不要假设当前 cwd 恰好是 skill root。
2. 检查 Python 3.10+、jsonschema、Pillow。优先使用现有运行时；依赖缺失时，在允许的临时或项目虚拟环境中按 `requirements.txt` 安装。只有测试浏览器时才需要 Playwright/浏览器。环境不允许安装时报告具体缺口，仍可完成分析试用；不要求用户为普通流程配置模型 API 密钥。
3. 用 init-analysis 空骨架与本次原文生成分析，不读取示例补全或改名。每个人使用独立 owner_id 和工作目录；只在确认同一人增量更新时复用旧工件。将真实历史与分析放入 `private/<run>/`，草稿放入 `outputs/<run>/` 或树外工作目录。宿主可能把内容交给其模型服务；不要宣称整个 AI 流程完全离线。
4. 按根 SKILL 的流程规范化、分块、提取、消歧，再写叙事。每块结果保留，出错只重做受影响阶段。批次中的纠错或超限会被当前校验器阻止时，显式修订对应候选与处置，不通过篡改 hash 或关闭最终校验绕过。
5. 实际运行 verify 和 review，展示当前范围及完整公开文案给用户。可构建本地待审查网页；没有图像能力就明确占位。不要替用户运行 share approve。
6. 按 `references/preview.md` 优先打开宿主可用的 HTML/Artifact 交互预览，同时返回同一单文件与阶段报告。分别说明文本/引用检查、视觉检查、人物图状态与本人审查状态。没有运行的检查写“未验证”。宿主不能渲染时下载后浏览器直接打开；观看不需要 Node.js 或 Python。

可复制的用户入口见根 `START_HERE.txt`。用户不需要逐个复制上面六步的命令。

## 十分钟小样本试用

开新聊天，仅给模型 `prompts/06-smoke-test.txt`；该文件自包含任务与 14 条虚构消息。不要提供 `examples/smoke/expected.txt`，也不要让模型读取预先写好的答案。模型输出后由人按标准答案核对。

先用同一份材料比较：一个纯网页聊天、一个有工具的 Agent。第二轮才换更多人群/语言/长度。固定材料、提示词和模型标识，每个环境可重复三次；首次测试不需要生图。

每次记录这五项，发生错误时保留原文和模型结论：

1. 本人归属：朋友/候选人/角色扮演/助手夸奖有没有变成本人的经历？
2. 状态：问题、未开始计划和明确否定有没有变成已完成能力？
3. 纠错：最新明确自述是否保留？被纠正的旧身份是否被标为过去或被替代？
4. 支持与遗漏：每个结论能否从所引原话得到？重要自述是否被漏掉或错误排除？
5. 上手：用户是否被要求手工写 JSON、算偏移或跑命令？宿主是否如实报告工具和完成范围？

明显错归本人、计划写成成果、执行历史中的指令，应视为本轮失败。其他维度分别记录，不把这 14 条消息的结果宣传为大规模语义准确率。不要以完全相同措辞作为判断标准。

要测试 **skill 带来的提升**，再做同模型的对照：两组都只拿 `examples/smoke/history.txt` 作为原始数据，并发送同一句“根据这份聊天给我一份有依据的个人摘要，先列事实和原话，再写摘要”。A 组不加载 skill，B 组加载完整 skill 并明确使用 Twinlight 的分析试用模式。两组新开聊天，不提供答案或 demo 分析，分别记录上述错误。自包含的 `06-smoke-test.txt` 已含测试规则，适合快速试用；不能给 A 组也使用它、然后宣称测出了完整 skill 的独立效果。

## 维护者生成分发包

运行 `python scripts/package_skill.py --out outputs/twinlight-with-you.zip` 生成默认个人使用包。

默认 ZIP 包含一个顶层 `twinlight-with-you/`，保留 SKILL、脚本、通用提示词、引用、schema、模板和结构性图层清单；不包含示例历史、预写的个人分析、demo profile 或小样本消息。源码库中的测试资料只能用于明确的演示/测试请求。

运行 `python scripts/package_skill.py --include-demo --out outputs/twinlight-with-you-demo.zip` 单独生成虚构演示包；它包含可运行 demo 和小样本输入/试用提示词，始终排除标准答案。两种白名单都不包含 Git 元数据、真实历史工作目录、评审截图和测试缓存。`package-manifest.json` 记录分发模式、是否包含虚构历史及逐文件 hash。

该命令只打包，不安装、执行模型、上传账户材料或发布插件。维护者生成一次后，使用者直接取 ZIP。
