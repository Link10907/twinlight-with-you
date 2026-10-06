---
name: twinlight-with-you
description: Create a personal Twinlight galaxy HTML and an embedded illustrated SSR card, preserving the approved V10 experience, detailed fantasy artwork, native image layers, parallax and foil. Use for a new personal Twinlight or updates to its content and card.
---
# Twinlight · 与你同光

默认在同一次请求中制作并一起交付 **个人星系单文件 HTML + 同一张原生分层 SSR 闪卡**。用户明确只要一项时使用对应模式。执行入口只有 [AGENT.md](AGENT.md)；不让用户选择内部参数或反复发“继续”。用户要求“在聊天里直接玩/渲染”时，把真实聊天内交互也列为本次交付条件，不能自行降为下载文件。

## 先保住作品，再替换个人内容

产品基准是用户认可的 **Twinlight V10 demo**：黑金星系、靠近才显现的行星、双星系连续交融、提问转场、完整揭卡页面、紧凑层内视差和随视角变化的镭射。页面、交互、shader、音乐由已有模板和 renderer 组装，**不交给语言模型重新设计**。构建时验证模板锁，交付时验证真实页面。

默认美术为 `twinlight-collector`：精细原创幻想收藏卡，主体有可信体积与材质、环境有空间、细节丰富但焦点清楚、精致金属卡框和固定文字。先看随包审美参考，再设计当前人的形象；只有用户明确要求换画风，才选择其他已安装风格。改变人物、动物、动作或故事，不自动改变 Twinlight 的美术语言。

**可复用的是设计，不可复用的是人格。** 固定模板、品牌风格、明确标为 `style_only` 的虚构无字参考可以读取和传给图像工具；作者、demo 和其他用户的经历、称号、角色设定与成品层不能套给当前人。本人肖像需要实际照片与授权；否则画原创概念形象。

## 最短生产链

1. 核对完整资源、V10 模板和本次宿主能力，确定实际预览入口，整理当前授权资料并冻结文案。
2. 按 [CARD.md](CARD.md) 选一个行为隐喻、一个主体和一个清楚动作；看参考，生成并审查无字原型。
3. 用图像工具在同一原型画布上原生编辑出背景、主体、少量前景，保住尺度与坐标；程序独立排字、装层。
4. 原图、合成、实际动态逐项验收，通过同一 public `run --layers` 嵌入固定页面；打开真实预览后，按导出的附件清单在同一最终回复中交付。

美术判据见 [质量工作流](references/quality-workflow.md)。图像工具负责插画；程序负责页面、精确文字和效果；实际看图决定美术是否达标。增加记录或检查项不能代替一张好看的原型。

## 完成判定

完整成品只认当前 `run-report.json` / `delivery-report.json` 中 `complete=true` 指向的文件。both 模式主文件必须是 `site-with-card/index.html`，通过 `scripts/deliver_artifacts.py` 导出。基础 HTML、静态海报、待验图层和效果截图不是完整双模块结果。

`complete` 表示构建完成；`request_satisfied` 才反映本次文件与预览要求是否满足。文件完成、本地动态通过、聊天内可交互预览分别报告。生图返回是中间结果，宿主还须继续装层、验收和导出；最后按真实 `handoff.json` 展示卡图、页面、独立预览和完整下载包。遇到能力缺口或有限返工仍失败，保留成功模块并说明具体缺口，不把缺项改成通过。默认私人未确认草稿，不自动公开；不携带字体文件、原始聊天或工具凭证。

需要逐句原话出处时读 [严格来源流程](references/workflow.md)；首次在某宿主运行、要求聊天内交互或能力不足时读 [平台适配](references/platform-adapters.md)；最终回复按 [交付协议](references/delivery-v2.md)。其他参考仅在相应步骤需要时读取。
