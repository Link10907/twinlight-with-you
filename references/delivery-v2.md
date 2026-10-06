# 文件完成与本次请求满足

`complete` 指本次请求文件、v2具体形象美术记录、原生卡内嵌、实际本地浏览器关口全部通过；不代表外部生成来源认证、不代表本人批准，也不证明聊天宿主能运行 HTML。`request_satisfied` 进一步检查本次明确的预览要求；二者都不能证明宿主已经把附件发给用户。

用户明确要求在聊天里直接渲染或操作时，首次 `twinlight.py run` 加 `--require-in-chat-preview`。要求保存在工作区，沿 `next_action.resume` 继续，不能在续跑或导出时丢弃。文件已完成但预览待测时，`request_satisfied=false`、`next_action.type=verify_in_chat_preview`；确认不支持或受阻时为 `report_host_limitation`。按 [平台适配](platform-adapters.md) 操作实际入口，不重生已完成插画。

both 的 primary_output 固定来自 html_with_card；原型、基础 HTML 和 candidate_outputs 都不能顶替。导出器根据当前 public receipt 复核实际文件 hash，仅复制最终 HTML、正面图、独立预览、便携卡包和简短说明。不要把字体、聊天原文、工具响应或内网地址放进交付包。

## 记录真实聊天内交互

未知时默认 `not_tested`。在 `RUN/host-preview.json` 写入实际观察，再按同一 public `run` 续跑刷新报告。`host-preview-2` 的字段如下，不用模板中的占位文字充当观察：

| 字段 | 来自哪里 |
| --- | --- |
| `version` | `host-preview-2` |
| `status` | 实际 `available` / `unsupported` / `blocked` |
| `surface` | 本条观察针对的入口为 `in_chat`；受阻或不支持时也记录这个尝试目标，不表示已经呈现 |
| `html_sha256` | 当前 `primary_output` 原文件字节的 SHA-256 |
| `tool`、`artifact_reference` | `available` 时必须提供实际工具名及它返回的原生入口或工件引用；入口预检即不支持或受阻时，可省略不存在的引用，在 observation 中记录具体限制，不虚构成功工件 |
| `observation` | 具体看到的结果或错误，至少 12 个字符；不能只写“通过” |
| `checks` | 以下适用交互的逐项对象；只有实际完成才写 `passed: true`，并写至少 12 字符的 `observation` |

- HTML 模式：`galaxy_navigation`、`galaxy_merge`、`question_transition`、`return_navigation`。
- card 模式：`card_parallax`、`foil_angle`、`fixed_typography`。
- both 模式：上述全部，再加 `card_reveal`，确认揭出的就是本次通过审美的同一张卡。

缺交互、哈希不符或只有旧 `host-preview-1` 时，不能满足明确的聊天内请求。旧记录保留兼容展示；完整 v2 观察对应 `in_chat_interaction_verified=true`。宿主观察不是独立平台认证，软件无法证明观察者没有虚报；下载成功、本地浏览器通过或静态截图均不能替代它。工具只能在最终回复才渲染且尚无法观察时仍保持未测。

浏览器检查固定 V10 页面载入、星系浏览、交汇、揭卡和返回；独立卡片检查原生视差、关 foil 对照、零 depth 对照、视角 foil、固定文字、真实拖动、触摸、键盘与减少动态。CSS fallback 可用于可见性和交互，但不算 WebGL foil 通过。

## 同一最终回复的交付材料

用 `scripts/deliver_artifacts.py --workspace RUN --out DELIVERY` 导出到独立空目录；实际 ChatGPT 文件环境的 DELIVERY 在 `/mnt/data` 下且支持沙箱附件时，加 `--link-style sandbox`。本地宿主默认 `local`。相同文件无需重新生成，不手工写另一套文件名或猜测 `/mnt/data` 路径。

导出器保留已完成文件，即使明确的站内要求尚未满足也允许取回，并将真实状态写进说明。新增 `handoff.json` 列出导出后的真实路径、哈希、大小、链接和卡图显示引用，`delivery-reply.md` 提供本次文件对应的回复材料；二者包含宿主路径，留在导出目录，不放进便携 ZIP。ZIP 内只保留宿主预览状态摘要，完整观察留在工作区。程序生成的 `delivery_sent=false` 表示它没有替宿主发送任何附件。

宿主读取材料，确认各引用可用，在第一条最终回复中一起给用户：正面卡图、主 HTML 的实际入口、独立卡片互动入口、完整 ZIP（内含便携卡包）。仅 HTML 或仅卡片时按对应清单交付。原生聊天预览引用另按本轮实际工具规则展示，不能把一个 Markdown 下载链接称为原生预览。

若用户明确要聊天内交互而 `request_satisfied=false`，用一句话指出尚未完成的体验，再交付已有文件，不说“全部完成”。浏览器或图片能力缺失时保留成功模块与准确未测状态；不能生一张“网页效果图”冒充运行截图，不自动部署任何用户私有内容。
