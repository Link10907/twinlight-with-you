# Twinlight · 一次请求编排

默认目标是当前用户的独立定义闪卡与实际单文件 HTML。HTML 与闪卡使用不同提示词、输入和验收；由你自动衔接，用户只发起一次请求。明确“只做页面”或“只做闪卡”时，只执行对应模块。

## 准备本次内容

找到实际项目目录；资源缺失时在获准目录取得完整仓库 https://github.com/Link10907/twinlight-with-you 。使用已有 Python 3.10+ 和 requirements；必要时在允许的虚拟环境安装。检查实际文件、执行、图像和预览工具，不要求用户克隆、操作命令或回答工具问卷。本文 `PY`、`TL` 代表实际 Python 与 `scripts/twinlight.py` 的绝对路径。

每个人独立目录。按 `references/lite-content.md` 将本次授权资料写入 `twinlight.json`。核对本人/他人、问题/能力、计划/成果与最新身份；不读 examples 补全。署名是本次实际总结者。HTML 数据不要求 `card.art_prompt`；美术放在独立 `card/art-brief.txt`，Strict 使用自己的 `art-direction.json`。卡模块只读内容，不改变称号、叙事或绑定。

资料充分时先完成本地未确认草稿，不停下来要求文案确认，也不代本人确认。无真实确认时不传 `--confirmed`，保持 `draft=true`、`share_allowed=false`。本人已明确同意确切当前文字时才沿用真实确认。资料确实不足时仅问必要的两三个短问题。

## 独立完成 HTML

读取 `prompts/html-build.md`，校验并用固定模板构建基础页面，不调用图像工具、不等待卡片。保存这个成功结果，供卡片未完成时直接交付：

```bash
PY TL lite-check <本次目录>/twinlight.json
PY TL lite-build <本次目录>/twinlight.json --out <本次目录>/site
```

实际已确认当前文字时才加 `--confirmed`。按 `references/preview.md` 检查实际文件与内嵌资源；浏览器不可用时交付文件并记交互未验证。有完成且匹配的卡包可直接消费。

## 独立完成闪卡

读取 `prompts/card-generation.md`、`CARD.md` 与 `references/art-direction.md`。本次 `twinlight.json` 为只读文字输入，也可明确使用 standalone `card-1`；无需星系数据才能制作卡片。由 AI 根据本次资料填写独立 brief，用户指定风格优先，不发审美问卷。

优先复用当前绑定且已检查的原生素材；缺少时按卡模块生成无字原型与真实原生层。禁止抠图、裁切、缩放或借别人的图凑通过。读取原型实际画布，独立精确排字。只重生成失败层，有效素材保留；有限重试与明确未完成模式按美术契约处理。

交付当前绑定的原生清单与素材、`card.json`、独立交互 `card/preview.html`。Lite/card-1 的独立正面可单独生成：

```bash
PY TL render-card <只读输入.json> --layers <完成的卡目录>/layers.json --out <本次目录>/card/front.png
```

这条命令只消费素材，不调用生图或构建星图。原型、两层兼容输入或占位正面不能冒充完整六层 SSR。Strict 沿用原 persona 绑定和独立卡预览接口，不从其 persona 伪造 Lite/card-1；正面截图只在实际预览后提供。

## 自动对接并一起交付

两者都被请求即包含对接意图。原生卡包完成并验收当前绑定后，自动再次调用 HTML 模块消费它；使用另一个输出目录保留基础成功页面：

```bash
PY TL lite-build <本次目录>/twinlight.json --layers <完成的卡目录>/layers.json --out <本次目录>/site-with-card
```

真实确认状态保持一致。HTML 不改图像或美术、不重新生图；导入失败仅修包/绑定或构建问题，不重画已成功卡片。无法完成卡片时，交付基础 HTML 与实际可用卡预览，说明卡片尚未完成；HTML 失败保留已完成卡片，先修对应问题。不要要求用户再发“生成 HTML”或“导入卡片”。

最后一起提供卡片预览和最终实际 HTML 的有效链接/附件，打开宿主支持的预览。只简短说明资料范围、实际图像模式和运行过的检查；内部 JSON、命令、素材包与报告留作可选附件。现代浏览器直接打开已构建的单文件，无需 Node.js、Python 或服务器。不能创建文件/执行代码的宿主如实报告缺口；查看器兼容路线只在用户选择后使用，不伪称一步已经完成。

`start --preview` / `next` / `check` 保留为兼容的串行本地草稿入口，执行者需自动走到 done；`render-card` 与 `lite-build` 仍可各自复测。默认两模块编排优先使用上述独立入口，HTML 成功不依赖 card 阶段通过。Strict 按 `references/workflow.md` 与 `references/extraction.md` 保留来源核对和本人审阅；公开发布另需明确指令，见 `references/privacy.md`。
