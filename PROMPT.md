# Twinlight · 一次生成

> v2.2 实际执行入口：[可执行接入](references/execution-adapters.md)。生图用 `execution.py image`，独立看图用 `execution.py review`；旧 dispatch/packet 仍只准备材料，不能代替调用。

根据当前用户授权资料，一次完成个人 Twinlight HTML 和同一张内嵌分层 SSR 闪卡，完成后一起展示。默认 `both`；明确只要页面或闪卡时用对应模式。

**保留已有 V10 作品体验。** 使用固定模板、原 renderer 和内嵌音乐；默认使用 `twinlight-collector` 精细幻想收藏卡风格。个人内容、主体与故事随当前人改变，页面和品牌美术不重新发明。

先取得完整同版本资源：已有 skill 包时执行 `scripts/bootstrap.py --root <ROOT>`；只有链接时先读取 bootstrap，再在允许目录执行 `--out <新目录>` 下载同一 commit 的完整项目。获取失败先检查当前完整离线包或已有完整仓库；无法恢复就明确资源缺口，不手写简化网页或代码插画作为替代品。

然后只按 [AGENT.md](AGENT.md) 执行总流程。绘画步骤读取 [CARD.md](CARD.md)：实际看随包无字审美参考，先做一个通过观察的原型，再用图像工具在该原型上原生编辑出同画布背景、透明主体与前景，程序排字和装层。参考的风格可用，旧人物经历、称号和成品卡不能套用。

按 public `scripts/twinlight.py run` 的 `next_action` 自动完成缺项并续跑；图片返回后继续组装，不以生图回复结束整项任务。成功卡通过 `run --layers` 接入同一页面。`complete=true` 与 `primary_output` 证明构建完成；用户要求聊天内操作时首次加 `--require-in-chat-preview`，还须满足 `request_satisfied`。用 `scripts/deliver_artifacts.py` 导出，依据生成的交付清单在同一最终回复中展示真实卡图、HTML、独立互动入口和完整包；both 模式来源为 `site-with-card/index.html`。

不让用户负责环境配置、参数选择或再次发继续。真实能力不足时说明具体缺口并保留成功模块。默认私人草稿，不自动公开。静态图片不等于分层互动，能下载文件不等于聊天内能执行 HTML。

本版先执行 AGENT 的宿主能力预检。独立审查是实际工具能力，不是文档中的角色名；无法隔离图像任务或创建视觉 Reviewer 时保留成功模块，不能宣称完整交付。

默认使用产物绑定的独立审查：真实独立任务能看图即可执行，不需要平台 session/call ID、签名 trace 或 OS 只读权限；这些缺项只记录，不停止。美术/原生层/动态/同版 HTML 仍必须实际通过。已有失败工作区先读 references/resume-v2-blocked.md，保留既有文案和页面，从未完成步骤续跑。
