# Twinlight · 与你同光

一次请求，得到你的个人星图 HTML 和专属分层闪卡。

## 一句话启动

把项目或完整 skill 包交给 AI，然后说：

> 根据你实际了解的我，生成我的定义卡，完成后直接给我看。

AI 会自动整理本次材料、生成页面和闪卡，再把完成的卡片接入页面；你不需要再发第二条生成命令。资料充分时直接完成本地草稿，只有必要资料缺失时才问两三个短问题。尚未审阅的内容如实标为草稿，不替你确认，公开发布仍由你决定。

- **有文件和执行工具的 AI**：读取 [SKILL.md](SKILL.md)、[AGENT.md](AGENT.md) 或 [PROMPT.md](PROMPT.md)，直接交付实际 HTML、卡片图片和独立互动预览。
- **只想做其中一个**：明确说“只生成个人星图 HTML”或“只制作专属闪卡”；两个模块可分别运行，闪卡说明见 [CARD.md](CARD.md)。
- **想要原话出处**：提供聊天导出并要求严格模式，保留来源核对和本人审阅。

AI 读不到项目时，可一次上传对应说明或完整包。明确没有文件/执行工具的聊天宿主不能保证一步完成；AI 应说明具体缺口，只有你选择手动导入时才使用 [离线查看器](https://github.com/Link10907/twinlight-with-you/raw/refs/heads/main/viewer.html)。查看器是可选工具，不是你的成品 HTML。

## 内容、卡图与观看

内容只依据本次授权材料，问题不写成能力，计划不写成成果；SSR 对所有人固定，不表示排名。保留你的美术提示，AI 自主补足未指定的设计，不让你填写审美问卷。整幅作品须有辨识度，不能给所有人同一张模板脸或同一只鹿。具体要求见 [美术说明](references/art-direction.md)。

HTML 和闪卡使用独立内部提示词，各自验收、各自修复。页面先独立构建，不依赖生图；卡片可独立预览，完成后自动接入同一人物的 HTML。卡片失败时保留成功的页面和明确标为未完成的卡片预览；页面失败时保留已完成的卡片，继续修页面。图片或数据不能代替实际 HTML，静态原型不能冒充分层闪卡。

页面保留 Twinlight V10 星系、双星交汇与揭卡。完整卡片使用原生独立图层、紧凑层内景深和视角驱动的 foil；独立互动预览也能查看这些效果。PNG 是正面预览，不烘焙动态闪光。

成品 HTML 用现代浏览器直接打开，无需安装 Node.js、Python 或本地服务器。网页内预览取决于宿主工具，HTML 不自动公开。GitHub Pages 只在维护者明确手动发布后作为可选入口；通用查看器独立下载，不进入默认 skill ZIP。

## 示例与私人材料隔离

默认使用包不含示例历史、预写人物分析或人物图。不同人的分析、布局和卡图分别保存，不能借用作者或其他人的经历。

- `examples/demo/`：完全虚构的严格模式测试材料。
- `examples/lite/` 与 `examples/generated-demo/`：完全虚构的人物与原生分层演示，仅在明确演示或测试时使用。
- `examples/showcase/`：历史作者个人展示，含真实摘要和少量原话；保留用于溯源，**不进入默认包、虚构演示包或通用查看器**。不得据此补全任何用户，也不据代码变更推定新的公开授权。

真人聊天导出、证据、照片、确认收据和运行报告放在忽略提交的私人目录。分享 HTML 也会分享其中的个人摘要与图像，是否公开由本人决定。详细规则见 [隐私与确认](references/privacy.md)。

## 给维护者和 Agent

| 工作 | 说明 |
|---|---|
| 一次请求自动完成两份结果 | [PROMPT.md](PROMPT.md)、[AGENT.md](AGENT.md) |
| 独立 HTML 构建与成品卡包导入 | [html-build.md](prompts/html-build.md) |
| 独立闪卡、卡包与互动预览 | [CARD.md](CARD.md)、[card-generation.md](prompts/card-generation.md) |
| HTML 内部内容格式 | [Lite 字段](references/lite-content.md) |
| 严格提取、原话核对与增量更新 | [工作流](references/workflow.md)、[提取规则](references/extraction.md) |
| 原型、独立图层与视觉检查 | [美术契约](references/art-direction.md) |
| 直接预览与平台边界 | [预览说明](references/preview.md) |
| 效果实验与分发 | [测试与使用](references/quickstart.md) |

HTML 输入不要求 `art_prompt`，美术只保存在独立 `card/art-brief.txt` 或 Strict 的 `art-direction.json`，不修改页面数据或人物绑定。闪卡支持只含卡片文字的 `card-1` 输入，无需 themes。完整卡片交付原生层及清单、`card.json`、`preview.html` 和 `front.png`；入口自动将匹配卡包用于最终 HTML。两模块失败只修对应部分，保留另一份已成功结果。

```bash
python scripts/package_skill.py --out outputs/twinlight-with-you.zip
python scripts/package_skill.py --include-demo --out outputs/twinlight-with-you-demo.zip
python -m unittest discover -s tests -v
```

默认 ZIP 只含 skill 与通用资源；演示 ZIP 另加白名单中的虚构数据，始终排除真人 showcase、标准答案、隐藏文件和私人目录。`package-manifest.json` 记录范围和文件哈希。生成新页面需要 Python 3.10+ 与 `requirements.txt`，由 Agent 处理；Node.js 与 Playwright 属于开发检查。

Lite 默认是尚未确认的有限印象草稿，保持 `draft=true`、`share_allowed=false`；真实本人确认另行记录，不伪造收据。Strict 保留源引用、状态与本人审阅。机械校验不证明语义蕴含，也不保证跨模型抽取完全一致；冻结数据与素材后构建才是确定性的。生图稳定性来自本次设定、原型、画布锁与验收，不是相同像素复刻。页面支持 1–8 个主主题，每个 0–8 个话题，不强行凑满。

保留 V10 光点流动、靠近才显行星、选中主体发光；先介绍当前 AI 星系，再以连续的双星系拉扯交融过渡至揭卡；有暂停、跳过与减少动态。卡片是分层视差与观察方向驱动的 foil，不是完整三维人体；本项目没有交付上游 Blender/GLB 流水线。

## License

原创代码采用 MIT；第三方来源见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。软件许可不自动授权个人历史、照片或生成图的再使用。
