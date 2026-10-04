# Twinlight · 给 Agent 的执行说明

用户只需说一次“根据你实际了解的我，生成我的定义卡，完成后直接给我看”。你负责从资料整理到独立闪卡预览和单文件 HTML 的完整编排。资料充分时直接完成本地草稿；卡片完成后自动接着构建 HTML，用户不需要再提出页面请求。JSON、图层包和内部命令不是有执行能力的 Agent 的最终交付。

## 准备与资料边界

1. 找到实际 skill root，复用其中的 `scripts/twinlight.py`，不假设 cwd。自己检查文件、Python、图像和交互预览能力；需要时在获准的临时或项目虚拟环境安装 `requirements.txt`。缺浏览器能力如实记录，不让用户判断是否能生图或配置模型 API Key。
2. 只用本次授权材料与可见对话，内容契约见 [PROMPT.md](PROMPT.md)。记忆是有限印象，不是原始消息。确实缺少必要资料时最多问 2–3 个短问题；已有昵称、偏好和授权不重复询问。
3. 每个人用独立 owner 与 workspace；只有同一确认本人和获授权工件才能增量复用。不读取 `examples/`、维护者或其他人的经历、称号、构图和卡图来填空。问过不等于掌握，计划不等于完成，助手夸奖和第三方故事不是本人事实。

`PY` 表示实际 Python 可执行文件，`TL` 表示 skill root 下 `scripts/twinlight.py` 的绝对路径。以下命令由你执行。

## Lite：一次请求完成本地草稿

默认开始：

```bash
PY TL start --workspace runs/<本次独立标识> --preview
PY TL next --workspace runs/<本次独立标识>
```

按 `next` 的 `do`、`write`、`then` 处理当前阶段，运行 `check` 并继续直到 `stage=done`。只写当前阶段需要的工件，保持本次 validated 数据、persona 与素材绑定一致。

- 内容阶段按 `schemas/lite.schema.json` 写 1–8 个主题；只够一个就一个，不凑经历。话题标注 `often / once / inferred`，总结者是本次实际写内容的 AI。
- `--preview` 在内容校验通过后将 review 阶段真实记录为 `skipped`（本人未确认），继续 art → build → visual。默认草稿保持 `draft=true`、`share_allowed=false`，不创建假确认收据，不用“可以”等 AI 自写回复代替本人 `confirm`。
- 若本人已经明确同意这份确切文字，使用其真实原话执行 `confirm --user-reply`；不要重复问。预览完成后取得真实确认也在同一 workspace 升级，继续 `next` / `check`，重做被打开的 art、build 和 visual 阶段直到 done。任何实质文字变化都不能沿用旧确认；可以先按未确认草稿完成，再让本人审阅。
- 只有用户明确选择先审文案时，才不加 `--preview`，展示 `preview` 的全部展示文字并等待本人确认。Strict 仍遵循原有审阅规则，不以 Lite 预览选项跳过。
- 技术错误按 `errors` 自修，修复后以 `unblock --note` 记录实际处理并继续；不把构建、路径、字体或校验问题交给用户。不要直接编辑 `state.json`、伪造确认或旧成功报告。真正需要本人补资料或作决定时才说明具体缺口。

本地草稿和文案确认都不等于授权公开发布；发布仍需要本人明确指令，见 [references/privacy.md](references/privacy.md)。

## 模块一：闪卡生成

读取 [prompts/card-generation.md](prompts/card-generation.md) 和 [references/art-direction.md](references/art-direction.md)。仅根据本次已校验的数据、persona 与风格生成卡图；称号和叙事在内容阶段冻结。Lite 的 `next` 提供 `card_spec` 与各层提示，Strict 使用 `art-brief`。无字 3:4 原型确定实际画布与构图，后续原生层都参考同一原型。SSR、中文、关键词和边框由程序独立准确排字；lineart 从最终 subject 同像素派生。

生成原型后按实际画布更新规格：

```bash
PY TL card-spec runs/<本次独立标识>/twinlight.json --prototype runs/<本次独立标识>/card/prototype.png --out runs/<本次独立标识>/card/card-spec.json
```

若记录了本次读图得到的构图锁，添加 `--composition runs/<本次独立标识>/card/composition.json`，遵循 `schemas/card-composition.schema.json`。不套用示例坐标，不把 alpha 中心当成面部或语义焦点。

不需要有内容的独立 spirit 时，装层命令为：

```bash
PY <skill-root>/scripts/prepare_card_layers.py --data runs/<本次独立标识>/twinlight.json --background runs/<本次独立标识>/card/background.png --subject runs/<本次独立标识>/card/subject.png --effects runs/<本次独立标识>/card/effects.png --prototype runs/<本次独立标识>/card/prototype.png --out runs/<本次独立标识>/card
```

可选 `--font <本机中文字体文件>`；使用构图锁时传入同一个 `--composition`。脚本检查画布一致并原样保存原生素材，生成独立 text、空透明 spirit 和配准 lineart。若设定确实需要中景象征物，保留本次生成的 spirit 并绑定到清单，不用空层冒充。

禁止抠图、去绿幕、棋盘转 alpha、裁切或重摆。每层首次生成后最多重生成两次，只修失败层，保留合格素材。仍不合格时显式降级并继续 HTML：

```bash
PY TL art --workspace runs/<本次独立标识> --static
```

`--static` 要求已有合格 prototype 或 portrait；没有则选 `--placeholder`。恢复原生层时选 `--layered`，重新验收并构建；模式互斥，优先于目录残留素材，不删除失败层、不自动升回分层。`generated` 不等于本人或视觉已 `approved`。

art 阶段自动生成独立的 `card/front.png`。需要单独复测闪卡模块时使用：

```bash
PY TL render-card runs/<本次独立标识>/twinlight.json --layers runs/<本次独立标识>/card/layers.json --out runs/<本次独立标识>/card/front.png
```

静态路线改用 `--prototype .../card/prototype.png`；已取得的原生背景/主体对可用 `--background` 与 `--subject`；无素材则为明确占位。这些输入路线互斥。命令只合成已有素材作正面预览，不调用生图；PNG 不烘焙动态 foil，raw pair 或原型也不能冒充已完成的独立 SSR 分层卡。

## 模块二：HTML 构建

闪卡通过验收或已如实降级后，立即读取 [prompts/html-build.md](prompts/html-build.md)，自动完成 HTML。模块只消费同一份 validated 数据和已验收素材，复用固定模板、星系动画与卡片交互；不得重新生图、改称号或另写 React 页面。失败只修构建或对应检查，不重跑已完成的内容和闪卡。

状态机用当前 `next` / `check` 完成构建。若需要独立复测 HTML，可直接使用：

```bash
PY TL lite-check runs/<本次独立标识>/twinlight.json
PY TL lite-build runs/<本次独立标识>/twinlight.json --layers runs/<本次独立标识>/card/layers.json --out runs/<本次独立标识>/site
```

只有本人实际确认当前确切文字才传 `--confirmed`；未确认草稿不传。静态路线用 `--prototype`，占位路线不传图像输入；不同图像路线互斥。Strict 用其 `build` 接口和当前审核工件，不能冒充 Lite 确认。

只有用户明确需要查看器导入素材时，才额外运行 `scripts/package_card.py`。卡包和 JSON 是中间工件，不能替代默认的卡图与 HTML。

## 查看与交付

读取 [references/preview.md](references/preview.md)。展示独立 `card/front.png`，并在宿主可用的 HTML/Artifact 预览打开同一次构建的 `site/index.html`。浏览器可用时检查载入、AI 星系介绍、双星系连续交融、主星进入、揭卡与返回；保留现有 V10 行为。新构建需要当前报告；实际检查失败先修，未运行的视觉/交互检查记未验证。

完成消息给出卡图和 HTML 两个实际入口，简短说明资料范围、分层/静态/占位模式以及实际检查。不能预览就提供单文件；用户用现代浏览器直接打开，无需 Node.js、Python 或服务器。源证据、确认原话和详细报告为私人可选附件，不嵌入页面。

明确没有文件/执行工具时才使用 [PROMPT.md](PROMPT.md) 的聊天兼容路线，并坦诚不能保证一次请求就完成卡片与 HTML。某次生图或构建报错应先在对应模块修复，不能据此直接把工作转交用户。

## Strict 执行

本人提供导出且要求逐句出处时，按 [references/workflow.md](references/workflow.md) 与 [references/extraction.md](references/extraction.md) 规范化、分块、提取、消歧、审查和构建。每条事实保留真实用户引文、精确偏移与哈希，每句展示文字关联本次已核对 fact IDs；不得用 `--preview` 跳过其来源和本人审阅。两份模块提示词仍适用，卡图绑定当前 semantic snapshot；按原规则取得必要审核后，内部完成卡片再自动构建 HTML。
