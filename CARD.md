# Twinlight · 独立闪卡流程

交付当前用户的原生分层闪卡：图层与 `layers.json`、便携 `card.json`、独立互动 `preview.html` 和正面 `front.png`。原型图片不能代替完整闪卡。默认由 [AGENT.md](AGENT.md) 在同一次请求中调用本模块并自动接入最终 HTML；用户明确只要闪卡时，也可独立运行，无需星系页面。

本模块不编写星系叙事或构建星图 HTML。内部范围、输入输出和有限重试见 [prompts/card-generation.md](prompts/card-generation.md)。

## 输入与美术

使用完整项目中的相对资源与脚本，由 AI 处理 Python 3.10+、requirements 与已授权图像工具。自己判断实际能力，不让用户运行内部命令。缺工具时说明具体缺口，保留已有预览，不能把静态图称为完整分层闪卡。

读取 [references/art-direction.md](references/art-direction.md)。每人使用独立卡片目录，保留用户明确提示、可见参考与最新修改。未指定的画风、形象和配色由 AI 自主选择，保证作品辨识度与完成度，不发审美问卷。

默认读取入口已校验的 `twinlight.json`，作为只读输入取得昵称、实际总结者和 card 文字；不能修改 HTML 内容来换画风。明确只做卡片、没有星系数据时，可单独写 `card-input.json`，遵循 `schemas/card-input.schema.json`：`twinlight="card-1"`、name、summarizer 与 card 的 title、english_title、keywords、tagline、reflection，无需 themes。两种输入的相同身份文字得到相同人物绑定。

Lite 可以先完成尚未确认的私人草稿，如实记录未确认状态，不默认等本人回复。已明确确认确切文字时沿用真实授权；`generated` 不等于本人 `approved`。Strict 保留原有来源核对和本人审阅，不借 Lite 草稿绕过。

美术只保存为独立 `card/art-brief.txt`（20–1500 字），不写入 HTML 输入或改动人物绑定。每层调用保留本次 brief、画布与职责。`PY`、`TL` 是实际 Python 与 `scripts/twinlight.py` 的绝对路径。

Strict 只读 history / analysis 与已编译 persona；将设计保存为独立 `art-direction.json`，按 `schemas/art-direction.schema.json` 写 visual_style、可选 symbols、portrait_mode 与真实 reference_consent。不写回 analysis：

```bash
PY TL art-brief <只读history.json> <只读analysis.json> --art-direction-file <卡片目录>/art-direction.json --out <卡片目录>/art-brief.json
```

Strict 卡包沿用当前 persona_digest。下方打包和独立交互预览命令省略 Lite 的 `--data`，不从 Strict 另造 card-1 来改绑定。两种来源只影响内容绑定，不降低美术标准。

## 生图、装层与交付

Lite 或 card-1 先取得规格；Strict 使用其独立 brief：

```bash
PY TL card-spec <只读输入.json> --art-prompt-file <卡片目录>/art-brief.txt --out <卡片目录>/card-spec.json
```

按美术契约生成无字 3:4 原型，锁定实际画布和构图，再直接生成同画布完整 background、原生透明 subject / effects 与可选 spirit。明确提示优先，未指定部分自主完善；线条、材质、比例、光线与动作应形成清楚且精致的整体，不套通用 AI 模板脸。保持同一原型参考和真实透明开关，不抠图、裁切、缩放或重摆。原型后以 `--prototype` 更新规格，可用 `--composition` 绑定本次实际读图得到的构图锁。

Lite/card-1 且没有有内容的 spirit 时，由项目脚本装层；SSR、中英文称号、关键词、标语、边框与实际总结者准确程序排字，lineart 从最终 subject 同像素派生。有内容的 spirit 须保留并绑定，不能被空层覆盖。

```bash
PY <项目>/scripts/prepare_card_layers.py --data <只读输入.json> --art-prompt-file <卡片目录>/art-brief.txt --prototype <卡片目录>/prototype.png --background <卡片目录>/background.png --subject <卡片目录>/subject.png --effects <卡片目录>/effects.png --out <卡片目录>/assembled
PY TL validate-art <卡片目录>/assembled/layers.json
PY TL render-card <只读输入.json> --layers <卡片目录>/assembled/layers.json --out <卡片目录>/front.png
PY <项目>/scripts/package_card.py --layers <卡片目录>/assembled/layers.json --data <只读输入.json> --out <卡片目录>/card.json
PY <项目>/scripts/preview_card.py --layers <卡片目录>/assembled/layers.json --data <只读输入.json> --out <卡片目录>/preview.html
```

Strict 按同一契约独立排字与登记图层，再用省略 `--data` 的 package_card / preview_card 命令。正面 PNG 可在实际独立预览中截图保存；无截图能力则交付原生卡包和独立互动预览，明确 PNG 未生成，不伪造 Lite 绑定调用 render-card。

`preview.html` 只展示当前卡片，复用同一真实景深和 foil 渲染器，不读取星系数据。打开它验收正面、左右、闪光、边缘和文字；构建预览文件不等于互动已验证。`front.png` 只合成已有素材，不调用生图，不烘焙动态 foil，也不能代替完整交互预览。

只修失败层，每层最多重生成两次；必要时按美术契约做一次明确构图修订，保留旧素材和记录，不重开无限重试。仍失败就保留原型或占位预览，明确卡片未完成，保留已成功的 HTML。卡片技术问题不改只读文字、人物绑定或页面。

成功后交付完整卡包、独立互动预览和正面图，入口自动将匹配卡包交给 HTML 模块，无需用户再次要求。接入失败只修导入，不重做卡片；HTML 失败也保留此卡片。仅在明确只做闪卡时止于本模块。公开发布仍需本人明确授权，见 [references/privacy.md](references/privacy.md)。
