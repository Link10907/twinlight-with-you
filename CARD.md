# 任务 A：只制作并验收一张闪卡

入口：`task-card`。本文件是宿主操作说明，不是生图提示；不读取 HTML.md、网页截图或星系叙事来画卡。保持精细幻想收藏插画、原生分层、固定排字和动态镭射。背景可以细致，但只服务当前主体与指定场景。

## 1. 冻结两个不同用途的输入

`card-input.json` 保存称号、文字、归属及实际总结模型，仅供程序排字和绑定。**不发送给图像模型。**

上层只写 `card-image-input.json`：已选画风；物种/性别呈现/年龄感；2–5个可见特征；服装、表情、一个动作和至多一个接触道具；简短环境、光线、构图和1–2个近景。不要传履历、抽象标签、星系比喻或选型长篇理由。字段见 [窄输入契约](references/card-input-contract.md)。

```sh
PY ROOT/scripts/visual_plan.py init WORK/card-image-input.json --persona-digest DIGEST --out CARD/art-direction.json
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --capabilities WORK/host-A.json
```

`init` 由程序附加私人归属与排字配置；`compile` 输出 `image-input.json` 和当前角色短提示。兼容旧 art-direction-2，但其 selection_basis、selection_reason、preferences、typography 均不进入生图。

默认 `twinlight-collector`；用户明确换画风才选其他已安装类型。实际绘画语言取自 `assets/art-styles/image-presets.json`，不是只发送 style_id。偏好若改变画面，应先落到相应形象/场景字段，不附一段自由文本。

## 2. 实际独立生图与原型审查

先按 AGENT 检查真实工具。每次只发送当前 `prompts/ROLE.txt`、job 明列的实际图片与合法图像参数。**不要发送本文件、整个 plan/dispatch、完整用户请求或其他聊天附件。** 编译和 dispatch 都不等于已调用模型；上下文推断型工具只有真实新任务可用时才能使用，不能在同一聊天里改称“画师”冒充隔离。

原型：生成一幅无字、无框的连续竖向插画。只附所选画风的随包 style_only 参考；不复制其中人物/动物/场景。原创角色不附任意外部图片。本人肖像另走实际照片授权路径，不能把整站效果图当人物参考。

实际调用与登记优先使用 [execution.py image](references/execution-adapters.md)；它已包含 dispatch/record，不重复预留。宿主原生路线则 dispatch → 真调用 → record。保留原图及真实请求/响应，不补造记录。

```sh
PY ROOT/scripts/reviewer.py packet --stage prototype --layers CARD/layers.json --out CARD/reviewer-input/prototype-1
```

只把 packet 中的阶段任务、窄审查输入、pending 模板和真实图片交给**另一个独立视觉任务**。按 REVIEWER 真实导入/绑定。原型未 accept 不做分层；错误物种/性别/多角色/界面拼贴不能靠裁图救成品。

## 3. 同一原型，三次原生编辑

原型通过后 `compile --phase layers`。每次唯一图像输入都是该原型，不再附风格样图、本人照片或前次聊天：

| 层 | 保留/移除 |
|---|---|
| background | 移除主角、接触道具和指定近景，原位补全不透明中远景 |
| subject | 原位保留主角及接触道具，移除环境和近景，其余原生透明 |
| effects | 仅原位保留指定近景，其余原生透明 |

保持完整画布、尺度、姿态、坐标与光线；不程序抠图、裁剪、缩放或挪位。每边1像素原生舍入沿既有显式映射规则，不改源图。spirit 默认同尺寸空层，不为凑层数加同伴。程序派生 lineart 并独立排字。

登记各层，使用 `prepare_card_layers.py`、`art_quality.py composite` 和 `visual_plan.py bind-composite` 组装；依照阶段 packet 做独立 composite 审查。命令参数见 [执行说明](references/execution-adapters.md) 与 [原生证据格式](references/art-evidence-format.md)。

## 4. 动态卡、交接与失败

`task-card --layers CARD/layers.json` 产生真实 front/preview/pack。核对文字；实测左右倾斜、foil关闭、depth=0对照、恢复镭射、翻面与手机。用 `capture_review.py --mode card` 采集绑定当前预览的证据，再生成 final packet；final 与 card release 都只审卡，不要求星系。

真实独立通过后沿同一 task-card 续跑，由 `seal-card` 重验并生成 `card-handoff.json`。B 只导入这个同版已验收工件，不重画。

返工用 `visual_plan.py repair`：每次只写一条不超过240字符的“位置＋缺陷＋修改”，新请求不叠加旧裁决。历史、字节绑定和每角色3次实际调用预算保留；只修失败角色。类型错误先核对实际输入再重做原型。

**缺能力或未通过时停止在 A，保留私人工作区；不另外构建带占位卡的整站、不给阶段 ZIP 冒充本次目标。** 调试页面只在用户明确要求时用 `--debug-placeholder`，不可进入正式导出。
