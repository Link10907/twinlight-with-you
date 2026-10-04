# Twinlight · 一次请求编排

默认目标是当前用户的独立定义闪卡与可直接打开的单文件 HTML。两个模块使用独立提示词，由通用程序记录进度和核验文件，由宿主 AI 完成资料理解、生图与真实看图。用户只发起一次请求，内部续跑无需再问“继续生成”或“导入”。明确只要 HTML 或只要卡片时，运行对应模式。

## 取得资源与本次内容

优先解开用户一次提供的完整 skill 包。本文 `PY`、`TL` 是实际 Python 3.10+ 与项目 `scripts/twinlight.py` 的绝对路径。执行 `PY <项目>/scripts/bootstrap.py --root <项目目录>` 检查完整资源、运行时及维护的模板锁；不要把“宿主有 Python”当成版本和依赖合格。

只有链接且资源缺失时，按 [PROMPT.md](PROMPT.md) 在允许目录取得 bootstrap 并执行 `--out <本次目录>/project`。bootstrap 解析实际 commit 后下载同一 revision 的完整资源；也接受 `--revision <40位SHA>`。保存获取记录，后续读取该目录的同版文档、脚本与模板。它不生图、不自动安装依赖；AI 在允许环境修复缺失依赖后重查。读取 GitHub 页面、查看器或入口文本不等于安装或执行成功。

按 [references/platform-adapters.md](references/platform-adapters.md) 自行检查文件、执行、图像、字体和预览能力。环境缺口不能通过自写一个相似页面解决；HTML 与独立卡片分别如实记为未完成，保留能够完成的模块。不让用户克隆项目、执行命令或回答工具问卷。

每个人使用独立空目录。根据当前授权资料和可见对话按 [references/lite-content.md](references/lite-content.md) 写 `twinlight.json`；不读 examples 或作者资料补全，不把他人经历、提问、计划或助手猜测写成本人成果。署名为本次实际总结者。明确只做卡片且没有星系数据时，使用 [CARD.md](CARD.md) 的 `card-1` 输入。

资料充分时先交付未确认私人草稿，不伪造确认；`run` 当前统一生成 `draft=true`、`share_allowed=false` 的草稿。本人已明确同意确切当前文字的授权仍有效，确需启用已确认导出时使用独立 `lite-build --confirmed` 并重新验收，不把它伪记为控制器已确认。Strict 需要逐句来源与本人审阅时，改走 [references/workflow.md](references/workflow.md)，不把 Strict 转为 Lite 绕审核。资料确实不足时仅问必要的两三个短问题。

## 调用控制器并自动续跑

Lite 默认调用以下通用 CLI，而不是自行列出完成步骤并口头宣称成功：

```bash
PY TL run <本次目录>/twinlight.json --workspace <本次目录>/run --mode both
```

只要 HTML 使用 `--mode html`；只要卡片使用 `--mode card`，输入可以为 `card-1`。有实际可用浏览器可传 `--browser <真实Chrome/Chromium路径>`；没有浏览器时使用 `--no-browser` 并保留动态未验证状态。程序排字可传 `--font <实际中文字体文件>`。检查器未运行不能记作通过。

控制器保存 `run-state.json`、`run-report.json` 与只读 `content.json`，构建并核验固定模板的基础 HTML，再独立处理卡包。读取它实际返回的状态、工件路径、错误及 `next_action`。缺图层时 `needs_card` 是内部待办，不是要求用户第二步；AI 继续独立卡片模块。`repair` 若附带 `pending_actions`，也完成其中独立美术待办，不因 HTML 故障停止卡片。输入一旦冻结不能在同一 workspace 修改；内容确需更新时新建目录，不删除状态或改绑定来伪装续跑。

按 `next_action.out` 将美术 brief 保存为独立 `run/card/art-direction.txt`；独立模块也可用 `card/art-brief.txt` 并通过 `--art-prompt-file` 传入。不写入 HTML 内容或人物绑定。按两份模块提示词执行本次需要的动作：[HTML](prompts/html-build.md)、[闪卡](prompts/card-generation.md)。缺素材时先检查真实生图、原生透明输出与中文字体，然后依据当前资料直接生成无字原型和原生层；程序负责排字、卡框、同像素线稿和装层。代码几何图、静态 SVG、他人的素材、抠图或缩放都不能冒充完整专属 SSR。保存真实工具返回、原型、各层和实际看图记录；只有失败层需要有限重试。

完成且匹配的图层包交回同一控制器续跑，用户不再发导入指令：

```bash
PY TL run <本次目录>/twinlight.json --workspace <本次目录>/run --mode both --layers <卡片目录>/assembled/layers.json
```

以上是图层已经完成时的调用例子；优先执行 `next_action.resume` 给出的实际参数列表，保留当前独立 brief 的 `--art-prompt-file` 与之前的浏览器参数。续跑保持相同输入、workspace 和模式，控制器产物保持未确认草稿。控制器保留基础 HTML，完成独立卡片工件并尝试接入最终 HTML。导入失败只修绑定、包或构建，不能重画成功素材、改上游文字、跳过验收或重写页面。

## 完成关口与交付

每份 HTML 保存 `template-receipt.json` 并通过 `verify-site`。它核对维护的模板锁，再从固定资源独立组装比对真实输出；文件存在、旧报告和模型口头说明均不能替代。锁文件属于发布维护资源，生产任务不得运行维护命令重新锁定修改后的模板来凑通过。

完整卡片的机械文件检查、真实生图、视觉意见与动态互动分别记录。`generated` 不等于本人 `approved`；原型、两层兼容或占位属于未完成原生闪卡。卡包齐全但未运行互动时只说“文件已生成，动态未验证”；控制器结束也不自动证明语义和审美。浏览器检查覆盖实际运行项目，长文字、手机、AI 星系介绍、连续交汇、揭卡、返回，以及卡片视差与闪光的观看检查按 [references/preview.md](references/preview.md) 和美术契约处理。

| 控制器状态 | AI 的处理 |
| --- | --- |
| `needs_card` | 保留已验收基础 HTML，自动完成 `next_action` 中的美术待办并续跑；缺工具或达到重试上限时说明卡片未完成 |
| `files_ready` | 所请求文件与实际浏览器检查通过；另核对内容、绘画与原型配准，不自动声称质量已认证 |
| `dynamic_unverified` | 所请求机械工件已生成，动态检查未完成；交付真实文件并明确该限制 |
| `partial_success` / `failed` | 读取具体错误，只修失败模块；保留成功工件，不能统称完整双模块成功 |

工件固定保存在 `site/index.html`、`card/front.png`、`card/preview.html`、`card/card-pack.json` 与接入后的 `site-with-card/index.html`。待生图规格和独立提示保存在卡片目录；实际是否完成以本次报告为准，不能因路径约定就声称文件存在。

最终只给实际卡片图片/独立预览和个人 HTML 的有效链接或附件，打开宿主支持的同一文件预览。内部 JSON、命令、素材与报告作为可选附件。按 [references/preview.md](references/preview.md) 区分文件完成、动态未验与模块未完成；不伪造路径。现代浏览器观看已构建的单文件不需 Node.js 或 Python，生成所需环境由 AI 处理。

独立 `lite-build` / `render-card` 保留作模块复测；`start --preview` / `next` / `check` 是兼容串行入口。Strict 仍使用自己的来源审核、构建与卡片绑定接口。公开发布另需明确指令，见 [references/privacy.md](references/privacy.md)。
