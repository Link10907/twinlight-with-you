# 双任务执行入口 · v10-split-1.0

一个工具包、两个独立工作区。`PY` 表示宿主 Python 3.10+；`ROOT` 为本包；`WORK` 为本次私人目录；`A=WORK/card-task`，`B=WORK/site-task`，`CARD=A/card`。A 与 B 不得互相嵌套。命令由执行宿主运行，不要求用户手工填审查表。

## 0. 确认实际运行资源

```sh
PY ROOT/scripts/bootstrap.py --root ROOT
```

已有上传完整包优先使用本包，不从网上重新拉旧 main 覆盖。先选择本次任务，只加载对应入口。A 读 CARD；B 读 HTML 和交接契约，不把生图配方、完整聊天或网页截图送入图像任务。

真正生图/视觉调用走 [可执行接入](references/execution-adapters.md)，或宿主已经存在的真实窄任务。`doctor` 只查配置；探针才有实际调用。没有服务/凭证/工具时指出准确缺口，不自动购买、不编造调用、不代签。付费/远程调用按实际授权执行，不因为准备了 dispatch 就声称已经画图。

- A：`execution.py doctor --config WORK/execution-A.json --mode card`；实际 Reviewer、浏览器探针后用 `execution.py host ... --mode card` 写 `WORK/host-A.json`。
- B：`execution.py doctor --config WORK/execution-B.json --mode integrate`；配置只含 reviewer 即可，实际探针后 `execution.py host ... --mode integrate` 写 `WORK/host-B.json`。这个 host 明确禁止 image 调用。
- 已有真实宿主能力表可直接传给任务入口；B 使用 `preflight.py check --mode integrate`，不得用 `both` 的生图要求阻断 B。

## 1. 共用资料，冻结卡面投影

依据当前授权资料写 `WORK/person.json`，格式见 [Lite 内容](references/lite-content.md)。然后：

```sh
PY ROOT/scripts/twinlight.py card-input WORK/person.json --out WORK/card-input.json
```

只提取姓名、实际总结模型和卡面内容，保留同一 `persona_digest`；不带星系内容进入 A。已冻结文件不覆盖不同版本。资料不足不编故事，未知模型版本留空。准备资料不是第三个创作任务。

## 2. 任务 A：只把一张卡做成

```sh
PY ROOT/scripts/twinlight.py task-card WORK/card-input.json --workspace A --host-capabilities WORK/host-A.json
```

按返回的真实 `next_action` 与 [CARD.md](CARD.md) 执行：原型任务 → 实际生图 → 独立原型 review → 原生编辑各层 → 独立合成 review → 程序排字/预览 → 实际动态验证 → 独立 final。所有原件和实际证据保存在 A 内，不使用临时目录之外的审查依赖。

默认 `execution.py image` 内部会派发、调用并登记，同一次调用不再单独 dispatch。原生宿主路线则 dispatch → 真工具 → record，二选一。返回的原图、响应和每次失败保留原字节。每角色有限返工不清零，不重画已合格层。

```sh
PY ROOT/scripts/twinlight.py task-card WORK/card-input.json --workspace A --host-capabilities WORK/host-A.json --layers CARD/layers.json
```

final 通过后仍需要 card release，而不是转去生成网站。使用真实当前 `A/card/preview.html` 的动态截图与观察：

```sh
PY ROOT/scripts/reviewer.py packet --workspace A --stage release --evidence ACTUAL_EVIDENCE --out A/reviewer-input/release-1
```

ACTUAL_EVIDENCE 由实际 `capture_review.py` 或受支持的真实浏览器观测产生，不手工写通过字段。独立任务依据 [REVIEWER.md](REVIEWER.md) 返回原始 JSON；用 `execution.py review --root A ... --activate` 或实际宿主的 `reviewer.py import` / `activate` 导入。随后沿同一 `task-card` 续跑重验。`task-card` 真正 complete 后自动封存；也可显式：

```sh
PY ROOT/scripts/twinlight.py seal-card --workspace A
PY ROOT/scripts/twinlight.py check-handoff A/card-handoff.json --input WORK/person.json
```

A 的终点是合格卡和有效私人交接，不需要星系页面。只请求 A 时在此结束。`seal-card` 不是放行开关，它会重新读取当前所有门禁。

## 3. 任务 B：导入同一张卡，完成整站

此阶段按 [HTML.md](HTML.md) 执行，不再读取图像配方或调用生图。

```sh
PY ROOT/scripts/twinlight.py task-site WORK/person.json --workspace B --card-handoff A/card-handoff.json --host-capabilities WORK/host-B.json
```

B 不接受 `--layers` / `--art-prompt-file` / `--font`，不会重新排版或编辑 A。来源缺失、旧批准失效时只报告 `card_handoff_blocked`，不得使用占位卡补齐。

B 自己验证完整 V10 剧情、内嵌字节、同版 renderer、双向导航和独立本地文件运行；整页独立 release 只能针对 `B/site-with-card/index.html`。页面问题在 B 修复，不要求 A 重新生图。最终导出见 HTML。

## 4. 续跑与旧工作区

同一任务沿返回的 `next_action.resume` 续跑，不为绕过失败更换目录。A/B 输入内容不可在已冻结工作区里偷偷替换；需要新版本时保留旧版本。只改主题星而卡面字段不变，A 的 persona 绑定仍有效；卡面文字变化需要对应新排字/审查，未受影响的插画不强制重画。

旧 `run --mode html/card/both` 保持原语义。旧 both 的卡尚未独立通过 A 门禁时，不能直接封存为已验收 A；可保留原图，用独立 A 工作区完成当前预览和必要审查，不必凭空重生同版原画。旧卡包没有 renderer 绑定时需由当前工具重新预览/打包并复验，再 seal。

本版私人交接使用 A 工作区实际路径。跨会话只要同一工作区仍存在即可；跨主机移动整份私人工作区需要重绑定实际路径并重验、再封存，不提供自动路径迁移。不把私人交接清单塞进公开成品 ZIP。

## 5. 交付状态

A 完成不能称“整站已完成”；B 完成也不表示附件已经发送、聊天平台支持交互或本人同意公开。读取真实报告，指出未通过/未验证的具体阶段。缺必需真实能力时保留真实已完成模块，别把候选当成品；不用更多提示文档冒充执行器已经接通。
