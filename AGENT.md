# 自动执行入口 · portable 默认

宿主 AI 自动完成本文所有内部步骤。`ROOT` 为完整包，`WORK` 为本次私人目录；A=`WORK/card-task`，B=`WORK/site-task`。

## 0. 取得本版完整资源

本次上传完整包优先，读取 SKILL.md 与本文件；不重新拉旧 main 覆盖。没有上传时，用已连接 GitHub 工具或已获准联网的代码运行器锁定 main 的 commit SHA，下载该 SHA 完整 ZIP 并安全解压，再读取入口。仓库 `Link10907/twinlight-with-you`，现有 `scripts/bootstrap.py --out ROOT --revision SHA --profile portable` 实现版本锁定和完整下载；不要只下载 PROMPT.md 后自己重写 V10。工具读取不到完整资源时精确说明，不谎称下载成功。

```sh
python ROOT/scripts/bootstrap.py --root ROOT --profile portable
```

portable 的资源预检不把 Playwright、WebGL、API key 或独立 Reviewer 作为生图前置条件；Pillow/jsonschema 是本地装配依赖，不是要求用户注册其他模型服务。依赖安装只在宿主允许的工作环境执行，不修改用户机器。

## 1. 根据真实工具选择分支

宿主观察工具列表和返回，把能力写到 WORK/capabilities.json，规范见 [portable-contract](references/portable-contract.md)。默认原生工具，不先跑 `execution.py doctor`，不探测/收集密钥。

```sh
python ROOT/scripts/portable.py plan --capabilities WORK/capabilities.json
```

image=available → full；明确 unavailable → html-only；unknown 继续检查可用工具，不问用户是否有 API；temporary failure 不改成无卡。判断的是当前服务当前会话，不按品牌。

根据实际了解的用户写 WORK/person.json，见 [Lite 内容](references/lite-content.md)。html-only 可省略整个 card 字段且不产生卡面总结。无真实资料时不要用示例人格补位。

## 2. 宿主驱动一次请求内的执行循环

```sh
python ROOT/scripts/portable.py run WORK/person.json --workspace WORK --capabilities WORK/capabilities.json
```

此脚本只编排/校验/装配，**不会自行调用当前聊天的内置 AI 工具**。宿主读取返回的 next_action，调用真实工具，保留输出，继续同一任务，直到完成；不把一次 CLI 返回当成任务结束。不向用户要求“回复继续”。平台确实强制结束当前回合或需要用户授权时如实说明，不能用本文件越权绕过。

full 缺图时，宿主先读取 run 返回的 style_selection；新卡按 [画风选择](references/style-selection.md) 完成选择，已有设计或原型直接沿用。选择是宿主内部步骤，不生成选择过程、方案比较或稳定性解释的播报。交给 A 的只有 card-image-input.json：version、style、subject、scene。图像调用使用既有编译器生成的任务文字及本任务真实参考图；宿主调度信息不拼入绘画请求。

A 按 [CARD.md](CARD.md) 执行。分别检查文生图、同图编辑与透明能力；先用 `portable.py layers-plan`，首个引用编辑换人/换场景就停止重复调用。按真实能力走 native_layers 或 assisted_layers，续跑 `--layers WORK/card-task/实际图层目录/layers.json`；续跑可省略已记录的 --layers，不重启制卡。A 图像和预览审查通过前 B 不构建。B 按 [HTML.md](HTML.md)，只用同一张通过审查的分层卡面。

html-only 自动走 B0；不读制卡手册、不跑卡片预检、不制作提示词、卡图或交接卡包。得到的主 HTML 无卡、无空槽，有完整结尾与返回。

## 3. 审查和有限返工

见 [REVIEWER.md](REVIEWER.md)。优先独立工具，没有则当前 AI 的真实视觉自检。仅无卡且无法看图的文本服务可按 REVIEWER.md 做源码/结构审查，记录 source_review_only，不能声称视觉验收。每项仅发送当前具体缺陷；每角色最多 3 次真实生成/编辑尝试，通过 record-image-attempt 记录同工作区，不重置计数规避额度；reference_mismatch 后停止同链路重试。不要因一层失败重画所有已通过图层。

返回 review_required 时审查实际当前目标，由宿主写 WORK/review-card.json 或 review-site.json，再运行同一命令。结果与目标字节绑定；不空填通过表。A 预览可用后按 [交互契约](references/interactive-card.md) 运行 verify_portable_card_browser.py，记录 WORK/card-runtime.json；有已知动态故障即阻断。缺浏览器记录未实测，不用静态图冒充动态验收。B 构建后把实际整站检查结果写 WORK/runtime-check.json。WebGL 和 file:// 无法验证如实记录；真实 JS/导航故障必须修复。

完成表示目标作品已构建且指定范围审查完成，不代表全部平台功能测试通过。`all_checks_passed=false` 必须随交付披露相应未测项。

## 4. 一次交付

```sh
python ROOT/scripts/portable.py deliver --workspace WORK --out WORK/delivery
```

full：主 index.html 内嵌同一张可交互卡；附 card-preview.html、可选静态留图与卡包。PNG 不是成品替代物。交付说明披露 layer_method、动态实测状态与 CSS/WebGL 差异。html-only：仅完整主 HTML 和简短交付说明；没有“待生成闪卡”。不要把私人源资料、审查记录、路径、密钥或字体复制到成品。

修改 skill 与生成个人作品是两种任务；修复工具包可交付 skill ZIP，但不能将它冒充用户个人 Twinlight 已完成。除非明确授权，不修改远程仓库。

## 严格模式

用户明确指定不可替代的独立任务或可验证上下文隔离时，读 `references/strict/AGENT.md`，使用旧 task-card → task-site。那些门禁仅在 strict 强制，不作为默认 portable 的失败原因。
