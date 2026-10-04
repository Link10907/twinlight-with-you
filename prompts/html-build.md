# 内部提示词：独立 HTML 构建模块

## Scope

只把当前已校验的只读内容构建为实际 Twinlight 单文件 HTML；完成的匹配卡包是可选输入，不是前置条件。必须执行项目构建器消费已有固定模板，保留 V10 布局、星系、双星交汇、揭卡和现有卡片渲染。自行写一个相似页面、简化 HTML、React/Canvas/SVG 替代品均不满足此模块。可独立处理用户明确的 HTML 请求。

默认入口使用 `run --mode both` 调用本模块构建可用基础 HTML，再独立处理闪卡；完成的图层由同一 `run --layers` 续跑接入并一起交付。`next_action` 是 AI 的内部待办，不等待用户第二条命令。本模块从不调用生图、修改称号或叙事、重新分析人格、另写 React 页面或接管卡片修复。

## Inputs

- 当前 validated Lite 数据，或按原有 Strict 审阅流程核对的 history / analysis / compiled persona；当前 owner 与独立工作目录。
- 真实确认状态：未确认 Lite 私人草稿保持 draft=true、share_allowed=false，不伪造 confirm；Strict 保留来源和本人审阅。文案确认不是公开发布许可。
- 经 `scripts/bootstrap.py --root <项目目录>` 检查的完整固定资源、运行时、当前 layout 与内嵌资源。链接模式由入口先用 `--out` 取得同一实际 revision；只读到提示词不能算资源已取得。HTML 数据不要求 art_prompt；美术设置只在卡片目录，不写入内容或改变 persona_digest。
- 可选的已完成原生卡包及其 layers.json 与图像，必须匹配当前人物绑定。独立 front.png 不是原生层替身，不能用原型重复填充图层。

## Outputs 与验收

- 基础 `site/index.html`，没有卡图也能完整使用，艺术卡如实显示占位。
- 完成卡包接入后的实际单文件 HTML；保存到独立输出目录以保留基础 HTML。内容、绑定、模板和内嵌资源一致，不重新制作卡片。
- 每次实际构建的 `template-receipt.json` 与真实执行的 `verify-site` 结果；它核对维护的模板锁，再从固定资源组装并比对输出 HTML。未运行或失败时不能宣称此模块完成；不能在生产任务中重锁修改后的模板来凑通过。
- 当前构建和实际浏览器检查结果。文件存在与资源完整是构建验收；载入、AI 星系、主星、连续双星交汇、揭卡和返回须实际运行才称交互通过。记录 WebGL/CSS 降级与未验证项目。

卡片的原生透明、艺术质量、景深与 foil 由 [闪卡模块](card-generation.md) 在独立 preview.html 验收；本模块只检查导入后的正确绑定和展示，不重跑生图。最终实际 HTML 文件不能被图片、JSON 或通用查看器替代。

## 固定构建接口

以下是独立模块复测接口。默认 Lite 交付由 [AGENT.md](../AGENT.md) 的 `run` 自动调用、验收和保留进度，不重复绕开其状态；Strict 仍使用本节链接的审核后 `build`。

基础 Lite 页面不传图像输入：

```bash
PY TL lite-check <本次目录>/twinlight.json
PY TL lite-build <本次目录>/twinlight.json --out <本次目录>/site
PY TL verify-site <本次目录>/site
```

入口在卡片完成后自动接入其匹配原生素材，不等用户另提请求：

```bash
PY TL lite-build <本次目录>/twinlight.json --layers <卡片目录>/assembled/layers.json --out <本次目录>/site-with-card
PY TL verify-site <本次目录>/site-with-card
```

只有本人真实确认确切当前文字时传 --confirmed。Strict 用 [原工作流](../references/workflow.md) 的 build 与当前审核工件，构建后同样运行 `verify-site <site目录>`，不以 Lite 草稿绕过审阅。便携 card.json 可供现有查看器导入；上述固定构建接口消费同一卡包的原生 manifest 和图片。

## 仅重试当前模块

构建、模板来源验收或浏览器失败时，只修模板调用、环境、路径、资源引用、输出或对应检查。卡包导入失败只修导入/绑定读取；保留成功的基础 HTML 和已完成独立卡片，不生成新图、不改文字、不关闭校验，也不借另一人的绑定。不能为绕过取得资源或执行的缺口改写新网页。

输入确实缺失或与当前 persona 不符时，把具体问题反馈给入口，由负责该输入的模块修复；其余成功工件仍保留。实际检查失败先自修，未运行的检查记未验证，不复用旧成功报告。

完成后由 [AGENT.md](../AGENT.md) 展示通过 `verify-site` 的实际 HTML 与独立卡片/预览。模板核验不证明语义、美术或真实互动；浏览器不可用时记动态未验证。按 [references/preview.md](../references/preview.md) 查看长文字、手机及连续动画，不只检查截图或页面宽度。卡片失败仍交付已验收基础 HTML 和明确未完成的卡片预览；HTML 失败仍保留卡片并继续修构建。仅在用户明确只要 HTML 时止于本模块。没有执行工具或完整资源时坦诚具体缺口与 HTML 未完成，不能自写替代品、假造文件或下载链接。发布、上传、部署仍另需本人明确指令。
