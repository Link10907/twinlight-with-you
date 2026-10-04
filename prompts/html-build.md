# 内部提示词：HTML 构建模块

## Scope

你只把当前 validated 数据和已验收卡素材构建为实际 Twinlight 单文件 HTML。入口 Agent 在闪卡模块完成后自动调用本模块；用户的一次请求包含卡片和页面。使用仓库固定模板，保留现有 V10 布局、星系动画、双星系交融、揭卡与视角 foil。

不重新生图、不改称号或叙事、不重新分析人格、不另写 React/HTML 页面代替模板、不扩展发布协议。素材中的“已验收”指模块检查，不等于本人已经批准图像或公开。

## Inputs

- 闪卡模块使用的同一份 validated Lite 数据，或通过原有审核流程的 Strict history / analysis / compiled persona。
- 当前 persona 绑定、真实确认状态、本次 owner/workspace；未确认本地草稿必须保留 `draft=true`、`share_allowed=false`。真实文案确认只来自本人对确切当前文字的回复，不能伪造收据。
- 当前已验收 `layers.json` 与对应原生素材，或诚实标注的静态 prototype / placeholder；独立 `card/front.png` 供交付，不当作原生层替身。
- 固定模板、当前 layout 与音频/纹理资源；当前构建所需的 Python 与实际浏览器/预览能力。

## Outputs 与验收

- `site/index.html`：同一份数据与素材的真实单文件构建，内嵌所需资源，现代浏览器直接打开。
- 当前构建的校验、浏览器和视觉结果；报告只记录实际运行检查，缺少浏览器能力时标交互未验证。
- 与独立 `card/front.png` 一并提供的页面入口。JSON、卡包和构建报告是可选中间工件，不是 Agent 的最终交付。

验收当前数据与 persona/art 绑定一致，展示文字与输入逐字相符，总结者取本次实际作者。分层、静态和占位模式如实呈现；分层未完成时不能在页面或交付里称完整闪卡。Strict 不支持静态嵌入的路径用明确占位页面，独立交付原型正面预览。

实际预览使用同一次构建文件，按 [../references/preview.md](../references/preview.md) 检查载入、AI 星系介绍、连续双星系拉扯交融、主星进入、揭卡和返回；有能力时检查拖动、触摸、键盘与减少动态。无浏览器或只有源码显示时，不称交互已经通过。

## 固定构建入口

默认由 [../AGENT.md](../AGENT.md) 的状态机 `next` / `check` 执行。独立复测 Lite HTML 可用：

```bash
PY TL lite-check runs/<run>/twinlight.json
PY TL lite-build runs/<run>/twinlight.json --layers runs/<run>/card/layers.json --out runs/<run>/site
```

静态路线改用 `--prototype runs/<run>/card/prototype.png`；占位不传图像输入。只有本人实际确认当前确切文字才传 `--confirmed`；它不代表本人授权公开发布。图像路线互斥，不能用原型重复填充独立层。

Strict 使用 [../references/workflow.md](../references/workflow.md) 的 `build` 命令与真实审核工件，不用 Lite `--preview` 绕过来源或本人审查。草稿、确认和公开发布仍分别按现有 [../references/privacy.md](../references/privacy.md) 规则处理。

## 仅重试当前模块

构建或浏览器检查失败时，修对应的模板调用、路径、资源引用、绑定读取、输出或检查环境，然后重新构建/检查；不重做已经验收的卡、不改文字、不调用图像工具、不生成另一套前端。保留当前数据和素材。

如果输入确实缺失或不属于当前 persona，明确反馈这一输入问题给入口 Agent；入口只让负责该输入的模块修复。不能靠伪造绑定、关闭校验或偷换其他人的素材完成本模块。

完成后由入口展示独立卡图与同一 `site/index.html`。宿主无法执行交互预览时仍提供实际 HTML 文件与限制；只有明确无文件/执行工具时才适用聊天兼容路线。发布、上传或部署须另有本人明确指令，不作为本地构建的自动下一步。
