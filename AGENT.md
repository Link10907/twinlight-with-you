# Twinlight · 一次请求编排

默认通过 **public `run`** 交付同一人的独立闪卡与固定模板 HTML。程序负责文件与关口；宿主 AI 负责理解材料、实际图像工具调用和看图。用户不用重复发“继续”或“导入”。

## 1. 输入与能力

按 [PROMPT.md](PROMPT.md) 取得同一 commit 的完整资源，运行 `scripts/bootstrap.py --root <项目目录>`。按 [references/platform-adapters.md](references/platform-adapters.md) 检查文件、执行、图像参考/透明、中文字体、浏览器；没有生图能力不能拿有 Python 代替。不要自动调用付费 API 或要求用户运行内部脚本。

每人独立空目录。按 [references/lite-content.md](references/lite-content.md) 写当前授权资料的 `twinlight.json`。只做卡片可用 `card-1` 输入。资料充分时生成未确认私人草稿；本人已有确切文字授权仍有效，但 public run 不据此虚构公开授权。Strict 沿用 [references/workflow.md](references/workflow.md) 的来源与本人审阅，不转 Lite 绕审核。

`PY`、`TL` 分别为实际 Python 3.10+ 与项目 `scripts/twinlight.py` 的绝对路径。

```bash
PY TL run <本次输入.json> --workspace <本次目录>/run --mode both
```

明确仅 HTML / 卡片时用 `--mode html` / `--mode card`。真实浏览器可传 `--browser <路径>`；不可用时用 `--no-browser`，不能据此声称动态完成。中文排字可传 `--font <真实字体路径>`。

## 2. 按实际状态执行内部待办

输入冻结为 `content.json`；同 workspace 不改内容、owner 或模式。确需变更内容就开新 workspace。独立美术设计保存在卡片目录，不注入 HTML 输入，不改变 persona_digest。

| 状态 | 内部动作与交付范围 |
|---|---|
| `needs_card` | 读 [美术工作流](references/quality-workflow.md)，准备并审查无字原型，再做独立图层；先保留已成功基础 HTML |
| `needs_art_direction` / `needs_art_evidence` | 补当前结构化设计或真实工具输出记录；不能补写虚假调用 |
| `needs_art_review` | 实际打开指定原型/合成/卡面进行评审；生成待填模板不算评审 |
| `art_rejected` | 按具体缺陷修失败层或原型，不能换 `passed` 或放宽约束 |
| `dynamic_unverified` | 当前文件可交付但动态未验，`complete=false` |
| `partial_success` / `failed` | 只修失败模块，继续 `pending_actions` 中独立模块的工作 |
| `files_ready` 且 `complete=true` | 所请求工件通过实际交付关口；仍不是外部模型来源认证或本人批准 |

缺素材动作先到 `prepare_and_review_prototype`，不是跳过原型直接凑图层。绘画分工见 [prompts/card-generation.md](prompts/card-generation.md)，命令见 [CARD.md](CARD.md)。具体美术原则可按需读 [references/art-direction.md](references/art-direction.md)。

## 3. 自动接入

同 persona 的完整图层、工具记录和三阶段评审放在同一卡片目录；`art-evidence.json` 与 `layers.json` 相邻。按当前 `next_action.resume` 续跑，保留输入、workspace、mode、字体、brief 与浏览器参数：

```bash
PY TL run <同一输入.json> --workspace <同一workspace> --mode both --layers <卡片目录>/layers.json
```

控制器生成可检查的卡面/独立预览，读取当前证据后才允许 HTML 集成。缺来源、未评审、被拒绝的卡仅位于 `candidate_outputs`。材料或评审变更后重新校验，不继承旧成功；基础 HTML 不被卡片失败丢弃。

HTML 模块只用固定 V10 模板并通过 `verify-site`，保留模板收据；生产任务禁止改锁过检。不能为赶进度改写另一张页面。已经成功的卡片也不因 HTML 故障重画。

## 4. 对用户的完成说明

交付真实 `outputs`，必要时另给明确标为“未完成”的候选预览。只看目录、manifest、`ok` 或 `art_status=generated` 不够。使用 public `run-report.json` 和 `delivery-report.json`；`complete` 同时要求文件、当前美术记录与真实浏览器检查。低层构建/旧兼容入口只作诊断，不能代替这一关口。

`art_reviewed_by_host` 是具名观察，不是用户确认；`generation_evidence_checked` 只说明记录与文件一致。`quality_verified` / `generation_provenance_verified` 保留 false，不伪造独立认证。所有私人输出仍 `draft=true`、`share_allowed=false`。

图片、单文件 HTML、独立预览的宿主展示检查见 [references/preview.md](references/preview.md)。下载链接可用不代表宿主能运行 JavaScript；真实浏览器与宿主未验证的范围分别说明。发布另需明确授权。
