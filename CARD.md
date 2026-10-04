# Twinlight · 独立闪卡流程

**交付当前用户的原生分层闪卡包：`layers.json` 与图层图片、便携 `card.json`，以及实际卡面预览和验收情况。** 不整理星系主题，不构建星图 HTML；两张原型图片不能代替分层卡包。

## 输入与美术

在本次允许的工作目录取得完整项目 https://github.com/Link10907/twinlight-with-you ，读取其相对资源与脚本。AI 使用可用的 Python 3.10+、requirements 与已授权图像工具处理技术步骤；工具缺失时报告具体缺口，不让用户执行内部命令。

读取 `references/art-direction.md`。每个人使用独立卡片目录，保留用户明确提示、可见参考与最新修改；未指定的画风、形象和配色由 AI 自主选择，不发审美问卷。

可直接读取已有 HTML 流程的 `twinlight.json` 作为只读输入，取昵称、总结者与 card 文字。没有 HTML 也可单独写 `card-input.json`，遵循 `schemas/card-input.schema.json`：`twinlight="card-1"`、name、summarizer 和 card 的 title、english_title、keywords、tagline、reflection；无需 themes。文字仍由本人核对，已确认的内容不重复确认。

美术设定保存为独立 `art-brief.txt`（20–1500 字），不要为换画风修改 HTML 输入或本人文字。旧数据已有 card.art_prompt 可沿用；独立 brief 优先用于本次图像调用。`PY`、`TL` 是实际 Python 与 scripts/twinlight.py 的绝对路径。

## 生图、装层与交付

```bash
PY TL card-spec <只读输入.json> --art-prompt-file <卡片目录>/art-brief.txt --out <卡片目录>/card-spec.json
```

按规格与美术契约调用图像工具：无字原型 → 锁定实际画布与构图 → 原生独立 background、透明 subject/effects 和可选 spirit。每次保留本次 brief 与真实透明开关，不抠图、裁切、缩放或移动主体。原型后以 `--prototype` 更新实际尺寸，可用 `--composition` 绑定本次构图锁。

无内容 spirit 时可由项目脚本装层；文字与线稿独立派生：

```bash
PY <项目>/scripts/prepare_card_layers.py --data <只读输入.json> --art-prompt-file <卡片目录>/art-brief.txt --prototype <卡片目录>/prototype.png --background <卡片目录>/background.png --subject <卡片目录>/subject.png --effects <卡片目录>/effects.png --out <卡片目录>/assembled
PY TL validate-art <卡片目录>/assembled/layers.json
PY <项目>/scripts/package_card.py --layers <卡片目录>/assembled/layers.json --data <只读输入.json> --out <卡片目录>/card.json
PY <项目>/scripts/preview_card.py --layers <卡片目录>/assembled/layers.json --data <只读输入.json> --out <卡片目录>/preview.html
```

有内容 spirit 时按契约独立生成并绑定，不能被空层覆盖。`preview.html` 仅展示这张卡，复用同一景深与 foil 渲染器，不读取星系数据，也不生成星图。打开它，按美术契约验收正面、左右、闪光、边缘和文字；报告实际做过的检查，构建预览文件不等于互动已验证。有限重生成与一次构图修订都只发生在卡片目录，失败不修改已有 HTML。静态原型是未完成闪卡的草稿；generated 不等于本人 approved。

最后交付完整卡包和实际预览，不只发图片。人物绑定由只读输入确定，独立 brief 不改变绑定；HTML 流程仅在明确导入时消费卡包，不负责生图。没有同一份内容/绑定时不能把卡包挂到另一人的页面。公开发布须本人明确授权，见 `references/privacy.md`。
