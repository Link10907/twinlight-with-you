# Portable：一次调用、一个任务、一个结果处置

本文件供宿主执行，不作为绘画输入。新 full 工作区自动使用 `portable-image-tasks-1`；没有额外账号、外部 API 或独立 Agent 门槛。脚本不调用聊天内置生图，也不能拦截宿主绕过流程自行发起的调用。

## 自动执行循环

先完成原有的内容与画风选择，再重复以下循环，不要求用户分步确认：

1. 运行原 `portable.py run`。读取 `image_task`；一次最多一个就绪任务：`prototype`、`background`、`subject` 或 `effects`。读取和续跑不消耗次数，不能仅凭 `ready` 重复调用工具。
2. 生图前执行 `reserve-image`，填写当前 `task_id` 和真实工具名称。取得 `drawing_payload`；它使用原短提示编译器，原型只引用选定画风参考及已授权肖像，图层只引用已接受的原型。任务编号、用途、次数、观察和个人资料留在执行层，不送入绘画。
3. 宿主通过当前工具实际支持的接口，调用一次。不要把内部 JSON 当作工具的通用参数，不使用弃用字段、不伪造文件引用；上下文是否隔离仍按真实能力记录。
4. 把本次实际返回的**全部**图片原字节复制到该任务的 `output_directory`，包括未采用图片。查看结果，由宿主写结果 JSON 并执行 `record-image-result`。回到 `run`，只执行新的明确任务。

```sh
python ROOT/scripts/portable.py reserve-image --workspace WORK --task-id ACTUAL_TASK_ID --tool ACTUAL_TOOL_NAME
python ROOT/scripts/portable.py record-image-result WORK/result-current.json --workspace WORK
python ROOT/scripts/portable.py run WORK/person.json --workspace WORK --capabilities WORK/capabilities.json
```

命令中的标识、工具名、返回路径必须来自实际任务，不是可直接当成完成凭证的示例。

## 返回结果字段

| 字段 | 含义 |
|---|---|
| `task_id` | 当前已预留、尚未登记结果的任务 |
| `outcome` | `success` 已返回图片；`failure` 调用失败；`reference_mismatch` 同图引用失败；`not_called` 确认尚未调用 |
| `disposition` | `accepted` 采用；`revise` 有具体视觉缺陷；`discarded` 不采用 |
| `reason` | 实际观察或失败原因，12–240 字符；不只是“通过” |
| `output` | 主要返回图片，相对 WORK 的真实路径；成功返回必须提供 |
| `extra_outputs` | 其他返回图片的数组，各项为 `file` 和具体弃用 `reason`；不会强行塞进作品 |
| `review_method` | 实际看过图片后记录 `self` 或 `independent`；后者另需真实 `execution_ref` |
| `repair` | 仅 `revise` 填写当前具体绘画缺陷，不包含历史裁决或页面要求 |

`success` 仅表示工具返回，不等于审美通过。失败或引用错位不能标为采用；有图片就保留原件并实际查看。没有调用就没有返回图片；调用是否完成不确定时保留 pending，检查真实调用记录，不猜测 `not_called` 来再次调用。预留也占用该角色三次预算，中断不自动清零。

损坏或无法解码的返回文件可保留为 `failure + discarded`，不填写视觉审查方法；这记录的是技术失败，不是看过图片或美术通过。

原型允许工具实际返回另一种合格 3:4 分辨率；接受后以实际画布为准冻结。图层必须保留同画布、相同位置与应有 alpha，不靠裁切缩放让不合格返回过关。

## 复用、失败和有限返工

已接受原型只作为后续图层的来源，不再启动第二张主题插画；已接受图层直接复用。第一次 `reference_mismatch` 停止当前原生引用链，按现有 `layers-plan` 检查辅助分层能力，不能重新抽画风、重启原型或伪装成没有生图能力。

辅助分层继续使用真实蒙版、完整背景及 `prepare_assisted_layers.py`，不改变六层接口；它的本地处理记录与生成图片任务分开。原生工具生成的素材必须登记；本地分割/修补由原 `layer-process.json` 追踪，不冒称原生生成。

仅 A 阶段已接受的某个图层被实际审查发现缺陷时，可执行：

```sh
python ROOT/scripts/portable.py withdraw-image-layer --workspace WORK --role subject --reason "实际观察到的当前图层缺陷"
```

保留被撤回原件和旧审查，清除该次装配缓存，继续同一角色剩余次数；不动其余合格层。接受原型不能通过此命令重画。A 放行后任务关闭，B 和交付只装配、检查同一卡片，不再生图。

## 交付核对与兼容边界

`run` 在 A 装配前、A 放行进入 B 时核对登记结果和最终源文件；`deliver` 再核对一次。原型须对应已接受任务，原生层须对应其实际返回，辅助层沿用现有像素与处理记录校验。待登记结果、未知返回文件、被替换却未撤回的已接受图层会阻止交付。

`image-tasks.json`、`image-usage.json` 和原始返回目录留在私人工作区。成品只带不含路径和观察原文的用途统计；未采用图有实际原因，但不用出现在 HTML 中。宿主交付时简要解释对话中已显示但未采用的图片，不虚构“隐藏封面”等用途。

旧工作区不补造调用前记录，不继承新的覆盖证明；续跑使用其原先锁定版本。旧 `record-image-attempt` 仅供旧工作区，新工作区使用预留与结果登记。无卡流程不创建图像任务。

检查范围只覆盖已登记调用和受管理的返回目录，无法发现宿主刻意漏报或在其他位置额外调用的全部结果；本地哈希不认证供应商、审美或上下文隔离。用户的一句话启动方式及平台安全/肖像要求不变。
