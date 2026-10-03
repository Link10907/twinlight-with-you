# Twinlight · 给 Agent 的执行说明

用户说“根据你实际了解的我，做我的 Twinlight，完成后直接给我看”时，由你完成资料整理、JSON、图像、校验与单文件 HTML。用户只需补充必要资料、确认内容并查看结果。

## 准备与资料边界

1. 找到实际 skill root；能访问项目的 `scripts/twinlight.py` 就复用，不假设 cwd。否则在获准的工作目录取得仓库或完整 skill ZIP。
2. 自己检查文件、代码、图像和交互预览能力。优先现有 Python 3.10+；需要时在临时或项目虚拟环境安装 `requirements.txt`。浏览器检查另需 Playwright 与浏览器；缺少时如实记录。不要让用户判断你是否能生图，也不要求其配置模型 API Key。
3. 只用本次授权材料与可见对话。记忆是有限印象，不伪装成原始消息；内容不足时最多问 2–3 个短问题。不要读取 `examples/` 来补全人格。不同人用新的 owner 与 workspace，同一人增量更新才可复用既有工件。

`PY` 表示实际 Python 可执行文件，`TL` 表示 skill root 下 `scripts/twinlight.py` 的绝对路径。下面的命令供你执行，不让用户逐个复制。

## Lite 执行

```bash
PY TL start --workspace runs/<本次独立标识>
PY TL next --workspace runs/<本次独立标识>
```

读取 `next` 的 `do`、`write`、`then`，按当前阶段处理并运行 `check`；直到 `stage=done`。内容格式见 `PROMPT.md` 与 `schemas/lite.schema.json`。

- 写内容：问题不等于掌握，计划不等于完成，助手夸奖或别人的经历不算本人事实。话题标注 `often / once / inferred`，有限范围的观察不得变成确定成就。
- 文案确认：展示 `preview` 的全部公开文字，等本人明确同意，再以其原话执行 `confirm --user-reply`。不要代确认；已经明确提供的授权和偏好继续有效。
- 技术修复：根据 `errors` 修复相应工件并重试。被状态机阻塞时说明具体原因，只询问需要本人补充的信息或决定；不要编辑 `state.json` 或伪造确认来解锁。

## 卡图：原型 → 原生独立图层

读取 `references/art-direction.md`。`next` 提供 `card_spec`、`prototype_prompt`、`subject_prompt`、`background_prompt`、`effects_prompt`、`spirit_prompt` 与 `text_instructions`；也可生成规格：

```bash
PY TL card-spec runs/<本次独立标识>/twinlight.json --out runs/<本次独立标识>/card/card-spec.json
```

1. 根据本次已确认的个人设定生成无字 3:4 `card/prototype.png`，锁定构图与视觉隐喻。主体可以是人物、物件或抽象形态；本次 `art_prompt` 中的形态、场景、风格与配色优先，不套月夜或人物模板。没有授权照片时不称为本人肖像。
2. 把原型作为图片参考，直接生成同尺寸、同坐标的完整不透明 background、真实透明 subject、effects 和可选 spirit。每次调用图像工具都明确透明背景开关及画布要求。
3. 保存 `card/layers.json`。程序独立排版 SSR、昵称、称号、关键词与边框为 text 层；lineart 从最终 subject 的相同像素派生。检查文字不遮住主要视觉焦点、景深紧凑、左右视角无重影或矩形边。

不需要独立中景同伴时，可用已有装层脚本完成第 3 步（脚本相对实际 skill root 解析）：

```bash
PY <skill-root>/scripts/prepare_card_layers.py --data runs/<本次独立标识>/twinlight.json --background runs/<本次独立标识>/card/background.png --subject runs/<本次独立标识>/card/subject.png --effects runs/<本次独立标识>/card/effects.png --out runs/<本次独立标识>/card
```

可选 `--font <本机中文字体文件>`。脚本原样拷贝已生成的背景、主体与前景，不抠图、不缩放、不重摆；按当前 SSR、称号、关键词、标语和总结者生成独立 text，spirit 留空透明，lineart 从 subject alpha 同像素派生，并自动写绑定清单。需要有内容的 spirit 时，保留本次独立生成的中景层并在清单中绑定，不用空层替代。

禁止抠图、纯色去背景、棋盘转 alpha、裁切或重新摆位。工具返回假透明或改变画布时重新生成对应层；无法取得合格图层时保留静态原型并说明。主体不能重复当背景或特效。

模式如实选择：独立图层 `layered`；只有原型 `static`；无生图能力 `placeholder`。`generated` 不等于本人或视觉已经批准，不用 `approved` 凑通过。

不走状态机时的构建接口：

```bash
PY TL lite-check runs/<本次独立标识>/twinlight.json
PY TL lite-build runs/<本次独立标识>/twinlight.json --layers runs/<本次独立标识>/card/layers.json --out outputs/<本次独立标识> --confirmed
```

`--confirmed` 仅在本人实际确认了当前文字后使用。原型静态图与占位路径按 `next` 指示执行；不要把图层缺口伪装成完成。

只有需要给纯网页查看器导入素材时，才额外导出便携卡包；默认仍直接构建 HTML 给用户。可选内部命令（脚本从实际 skill root 解析）：

```bash
PY <skill-root>/scripts/package_card.py --layers runs/<本次独立标识>/card/layers.json --data runs/<本次独立标识>/twinlight.json --out outputs/<本次独立标识>/card.json
```

这会封装已有原生图层并核对当前人物绑定，不重新生成或裁剪图像。用户只需导入文件，不需要理解内部数据格式。

## 查看与交付

优先在当前宿主的 HTML/Artifact 预览打开实际 `site/index.html`。检查载入、进入主星和打开卡片；有可用浏览器时运行项目检查。只有下载/源码展示时标注交互预览未验证。

给用户简短说明：已生成的页面、卡图是分层/静态/占位、是否真实运行浏览器检查。`report.html` 与详细工件作为可选附件；确认原话和源证据不要嵌到公开页面。不能预览时提供单文件，浏览器直接打开即可。

生成本地草稿不等于获准公开。没有明确发布请求，不上传或部署。详细边界见 `references/privacy.md`。

## Strict 执行

本人提供导出文件并要求逐句原话出处时，按 `references/workflow.md` 的严格流水线规范化、分块、提取、消歧、审查和构建。同一套原型与独立图层流程继续适用；卡图与 semantic snapshot 绑定，不复用其他人的素材。
