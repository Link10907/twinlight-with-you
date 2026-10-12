# 上游画风选择：选一次，下游只执行

本功能只决定已经安装的哪套画风用于一件新作品，不改画法，不降低完成度，也不改分层或动态渲染。上游是了解当前用户与具体形象的宿主；不是让图像工具临时从菜单里挑。

## 优先级与稳定边界

已开始的设计/原型优先沿用；对新卡，用户明确指定优先，其次上游明确指定，否则默认 `subject_random`。用户要求纯随机时选 `random`。六个实际 id/version 读取 `portable.py style-status --workspace WORK`，不得编造未安装风格，或把未支持的“纯水墨”等要求静默映射成工笔青绿。需要新画风时准确报告，不擅自改现有预设。

- `explicit`：提供 `style={id,version}`。即使外层仍带默认随机 mode，明确 style 优先；与显式候选限制冲突时报错，不偷偷改选。
- `random`：在提供的候选内等概率选择；不提供候选则全部六种。
- `subject_random`：宿主根据具体主体、动作、场景与用户明确的视觉要求保留至少两种候选，简短记录理由，再随机选择。没有更窄偏好则全部六种，不回落为固定 collector。只适合一种时用 explicit，不把单候选称为随机。

筛选不要把职业、性别、物种与画风永久绑定。例如修理机械鸟的青年既可以用未来风，也可用摄影、幻想或纸艺；不能因为用户写代码就永远选未来风。不为了风格改人物、物种、动作或增加无关道具。已有清楚场景应保留，不向上游形象字段追加第二套画法。

随机在新作品开始时发生一次，正常运行不固定 seed；脚本生成 seed 并保存在私人选择记录。明确提供相同 seed 和相同候选可复现抽取，seed 不从用户名/人格哈希推导。随机仍可能重复；本版不新增跨会话历史、轮转抽牌或保证不重复的状态系统。

## 宿主执行，不要求用户填表

先按原流程运行 `portable.py run`。新卡返回 `style_selection` 后，宿主写 `WORK/style-request.json`：

- `version`：`style-selection-request-1`。
- `subject`、`scene`：原 `card-image-input-1` 中的同名具体形象字段，保持原有字段限制，不带身份履历或网站内容。
- `mode`：可省略，默认 `subject_random`；`style` 为可选明确指定的 id/version。
- `candidates`：可选的已安装 id 列表，不可重复；`subject_random` 显式提供候选时还需 `reason`。
- `reason`：只保留在私人选择记录的简短筛选依据。
- `seed`：可选短字符串，仅复现实验时指定；常规新作品省略。

```sh
python ROOT/scripts/portable.py select-style WORK/style-request.json --workspace WORK
```

命令输出 `WORK/style-selection.json`（私人选择记录）和 `WORK/card-image-input.json`（原有绘画输入格式）。`selected_style`、`style_reference_images` 来自同一个已冻结的 id/version。选择器不调用模型，不假装自动读懂形象；兼容候选由上游提出，代码只验证、抽取和锁定。

接下来完全沿用原制卡路径：以此 `card-image-input.json` 生成既有短提示与原型；只用所选风格自己的参考图，没有参考图时使用所选文字预设，不能补上 collector 的参考图。原型通过后仅编辑该原型，图层阶段不重投风格菜单。`visual_plan.py init/compile`、分层、排字和主 HTML 装配接口不变。

**选择记录、候选、理由和种子绝不送入生图。** 给下游的是原 `version + style + subject + scene` 四个字段，仍由既有编译器读取 drawing/materials/palette。不要改 `image-presets.json` 来实现随机。

## 续跑和旧任务

同工作区再次 select-style 必须得到同一输入；保存的记录、画风/预设/参考哈希、具体形象和候选均核对。候选顺序变化不影响抽取；改变候选、种子、主体或风格需新工作区，不覆盖旧卡。缺失的 card-image-input.json 可由同一记录恢复，但不得覆盖不同内容。

已有旧版设计、原型或图层且没有选择记录时，继续原任务，不能以本版缺少记录为由重新生图或补做随机选择。底层 `default_style()` 和目录 `default_style` 保留旧调用兼容；它们不再是新卡自动选择规则。显式 strict 的原有独立审查和原生层门禁不放宽。

选择器锁定的是制作输入与资源，不是对画风美学的自动判定。原型是否实际遵循所选画风、分层是否保持一致仍须原视觉审查；不能用选择记录或测试通过冒充真实成图验收。主 HTML 仍内嵌同一张可交互分层卡，PNG 只作纹理或留图。
