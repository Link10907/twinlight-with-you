# 内部提示词：闪卡生成模块

## Scope

你只完成当前人的闪卡与独立正面预览。输入内容在上游已校验；保留称号、关键词、叙事和当前 persona，不重新分析人格或修改这些文字。不读取作者、demo 或其他人的素材。此模块不构建 HTML，也不负责公开发布；完成后把验收素材交给 [html-build.md](html-build.md)，入口 Agent 自动继续。

Lite 本地草稿可使用未得到本人确认的 validated 数据，诚实保留未确认状态。Strict 仍须遵循 [../references/workflow.md](../references/workflow.md) 的来源核对和本人审阅。不得把草稿、程序通过或 `generated` 标成本人 `approved`。

## Inputs

- 本次 validated Lite 数据，或通过 Strict 来源核对的 analysis / compiled persona；当前 `persona_digest` 与独立 workspace。
- 当前卡片文字、`art_prompt` / `art-brief`、用户已授权的风格与配色；仅有授权照片才表现本人长相。
- 当前 `card-spec`、原型（若已有）、本次构图锁（若使用），以及该 run 已合格的原生层。复用只限当前绑定，不借用其他人的图像。
- 实际图像、文件、排字和预览能力；没有生图能力如实选择占位，有合格原型则可静态降级。

## Outputs

- `card/prototype.png`：有图像能力时直接生成的无字 3:4 原型，记录实际宽高与构图。
- `card/layers.json` 与其绑定素材：分层成功时含完整 background、原生透明 subject / effects / 可选 spirit、同像素 lineart 和准确程序 text。层共享原型的实际画布与坐标。
- `card/front.png`：独立可看的正面预览，由当前素材合成。状态机 art 阶段自动生成，也可单独运行 `render-card`。PNG 只显示正面，不烘焙动态 foil，不证明浏览器视差已经验证。
- 真实的 `layered / static / placeholder` 模式和机械、视觉检查结果；未运行的检查标未验证。保留素材和本次绑定，交给 HTML 模块。

静态或占位不需要伪造原生 layers；原型或 raw background/subject pair 预览不代表准确 text 与全部独立层已经完成。没有图像时明确交付占位和视觉 brief，继续生成页面。

## 工作与验收

按 [../references/art-direction.md](../references/art-direction.md) 执行完整美术契约：

1. 当前 `art_prompt` 决定主体、场景、行为隐喻、风格和颜色；未指定时用精致手绘幻想插画，主体可以是人物、动物、物件或抽象形态。无授权照片时称原创概念，不称本人肖像。
2. 直接生成无字、无 SSR、无卡框、无水印、无预烘焙 foil 的 3:4 原型。读取实际合法画布，锁定姿态、尺寸、位置、光源和排字留白；比例错误重生成，不裁切纠正。
3. 每次图像调用都引用同一原型并声明实际宽高和构图。直接生成完整不透明背景及真实透明主体、稀疏前景和需要的中景层；透明层调用必须开启真实透明输出。禁止抠图、去绿幕、棋盘转 alpha、裁切、缩放或重摆。
4. 程序逐字排版当前 SSR、中英文称号、关键词、标语、边框与实际总结者；昵称显示在页面中。文字固定 depth=0，不让图像模型画字；lineart 从最终 subject 同像素派生。检查中文字体、字形、遮挡和安全区，不擅改标题来适应布局。
5. `validate-art` 检查画布、alpha、绑定与资源；实际看原型、各层和正面预览，背景无第二主体、无重复手持物、无矩形透明边，主体配准且焦点清楚。机械通过不代替看图。
6. 正面预览通过后交给 HTML 模块；完成页面后的 visual 阶段才在实际浏览器中验收左右视角、文字固定、关闭 foil 后的层内视差、拖动与翻面、触摸/键盘和减少动态。此模块不为动态验收另建页面，未运行的检查如实标未验证；正面 PNG 不能证明动态效果。

## 仅重试当前模块

图像失败只重生成失败层，保留同一原型、构图锁与合格层；首次生成后每层最多再生成两次。技术失败只修当前路径、绑定、字体或装层问题，不修改文字或借图凑通过。修复后的验收重新运行，不复用旧报告。

达到重生成上限或工具确实不支持原生透明时，选择实际可交付的 `static`；无合格原型则 `placeholder`。保留失败素材，写清未完成分层，并把当前正面预览与真实模式交给 HTML 模块继续。不要因卡片降级停止整次请求，不启动无限生图或自动付费 API。

单独复测分层正面（`PY` / `TL` 定义见 [../AGENT.md](../AGENT.md)）：

```bash
PY TL render-card runs/<run>/twinlight.json --layers runs/<run>/card/layers.json --out runs/<run>/card/front.png
```

静态用 `--prototype runs/<run>/card/prototype.png`；原生背景/主体对用 `--background ... --subject ...`；无图输入为明确占位。图像路线互斥。该命令仅消费已有素材，不重新生图、不构建 HTML。
