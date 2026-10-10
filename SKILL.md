---
name: twinlight-with-you
description: Produce Twinlight in two explicit tasks. Task A creates and independently reviews a native-layer fantasy SSR card. Task B imports its released artifact and embeds the same card in one self-contained V10 galaxy HTML with in-page navigation. Task B never generates or edits images. Real isolated image calls, independent visual review and browser evidence remain required where applicable.
---
# Twinlight · 与你同光

版本：`v10-split-1.0`。**一个包，两个制作任务，一个主 HTML。** 先读 [AGENT.md](AGENT.md)，再按本次任务读取一个入口；不要预加载另一项任务的完整上下文。

| 任务 | 入口 | 输出与边界 |
|---|---|---|
| A：制作并验收闪卡 | [CARD.md](CARD.md)，`task-card` | 原生分层、排字、互动预览、真实独立 final / card release；封存私人交接清单。不制作星系。 |
| B：制作星系并集成卡片 | [HTML.md](HTML.md)，`task-site` | 验证 A 交接，复制同版卡片，装配 V10、同页跳转、完整剧情与独立集成 release。不生图、不改卡。 |

默认先完成明确请求的那一个任务。用户只说“开始制作”且还没有已验收卡片时，从 A 开始；A 完成就给出其真实结果与交接状态，不暗中把 A 扩展成整站任务。用户明确要求两项一起时，也必须用两个独立工作区顺序执行 A → B。两个任务的完成状态不能混称。

## 不变的作品标准

保留原始 V10 星系、光点全景、靠近才显示的行星、主体发光选中、连续双星交融、按实际总结模型署名的提问、揭卡、翻面、紧凑原生分层视差和视角驱动镭射；交融不超过 15 秒。原 V10 核心、shader 和音乐不重写，不更新旧模板锁；新增导航有独立扩展锁。

默认 `twinlight-collector` 精细原创幻想收藏卡：明确焦点、可信材料、完整场景、前中后景。先看所选画风参考，再设计一个主体和一个动作；主体简洁不是低细节。原画无字无框，排字和镭射由程序产生。不用静态图、代码插画或复制海报层替代原生分层。

只使用当前授权资料。共享 `person.json` 及其 `card-input.json` 投影；称号、文字、归属和总结模型绑定一致。计划不写成成果，提问不写成能力；未经本轮照片与授权，不画本人肖像。不给其他人的卡换名字冒充当前作品。

## 真实执行与审查

A 预检真实图像任务隔离、参考传入、原生编辑/透明输出及独立视觉任务；B 的预检模式是 `integrate`，仅需实际浏览器与独立审查，不能因为没有生图账号而失败。独立任务可以使用已授权宿主工具或 [执行适配器](references/execution-adapters.md)，但本包不提供账户、凭证或额外模型服务。

生产者不能自签。Reviewer 读取真实原件，给出 accept / revise / blocked；缺平台 ID 或强制只读权限可如实记录，不等于免除真正独立任务。程序校验真实响应、字节与审查目标，不认证供应商身份。必须遵守实际工具的接口，说明文字不能激活不存在的能力。

## 交接与完成

A 只有当前卡片、动态和独立 release 均通过，才能 `seal-card` 生成 `card-handoff.json`。B 不能只读一个 `approved=true`；导入、集成后和导出时均重读 A 实际证据，比较图层、深度、版式和渲染器。详情：[交接契约](references/card-handoff.md)。

B 的 `index.html` 已内嵌同卡、脚本、样式、音乐与个人内容；`#galaxy` / `#card` 同页切换，保留 `#finale`。完整剧情和快捷入口汇入同一张卡，不使用 iframe；返回恢复同次会话的星系状态。`card-preview.html` 只是附加入口，不是主页面依赖。

`files_built` 不是通过；`complete` 还需要真实技术关卡与独立裁决；明确要求聊天内交互时另检查 `request_satisfied`。只通过 `deliver_artifacts.py` 导出当前放行工件。候选、CSS fallback、合成单测、截图变化不能冒充艺术验收或 WebGL 通过。主文件离线浏览器成功也不证明聊天附件可交互。

默认私人草稿，不自动 push、部署或公开。不导出原始聊天、审查日志、凭证、私人路径或字体文件。旧 `run --mode html/card/both` 保留兼容，不作为这次双任务工作流的新入口。
