---
name: twinlight-with-you
description: One-instruction native-AI Twinlight workflow. Acquire the complete pinned package automatically. Default portable mode uses the host's native image tools for a reviewed layered collectible card and embeds the same card in V10 HTML; when image tools are genuinely unavailable, create a complete card-free V10 galaxy HTML. Prefer independent review, otherwise record actual self review. Never require an external API account by default.
---
# Twinlight · 与你同光

版本：`v10-portable-1.2.2`。先读 [AGENT.md](AGENT.md)。默认交互只有一次请求和一次成品交付，不要求用户选择 A/B、下载 Git 包、运行脚本、配置 API 或手填审查 JSON。

## 先判定功能，再组织任务

- **原生生图可用**：内部 A→B；A 制作和检查可交互分层闪卡；原生层优先，引用编辑不可靠时按真实能力使用可追溯的辅助分层，B 只嵌入同一卡片与 V10 星系，不二次生图。
- **本次会话确实没有生图能力**：直接 B0，无卡星系为完整目标；无需 card 内容、生图提示、卡包或任何卡片审查。移除卡片 DOM、图片、入口、领取承诺，交融后有正式结束与返回。
- 未检查、无外部 API key、没有独立 Agent、浏览器不能启动 WebGL，都不等于没有生图。实际生成失败或额度不足不得冒充无生图能力。

[默认能力契约](references/portable-contract.md) 高于归档 strict 文档在 portable 中的执行要求；美术、隐私、真实输出和数据绑定标准不变；portable 可使用明确标注的 assisted_layers，strict 原生层要求不变。若用户显式坚持真正独立审查/完全隔离，则进入 strict，缺能力如实阻断，不用自检替代。

## 保留的作品标准

保留 V10 光点全景、近景行星、发光选中、星系旋转、连续不超过 15 秒的交融和音乐。完整模式保留模型署名、揭卡、拖转、翻面、自动轻摇、独立图层视差和 WebGL 镭射。主 HTML 内嵌同一卡片，支持星系与闪卡相互返回；无卡模式没有这些卡片功能，也不伪造它们。

保留精细原创收藏卡的完成度，使用一个明确主体、一个动作、一个确定画风。画风为启动句末尾可选项，未指定从全部已安装画风随机一次。宿主依 AGENT.md 完成选择，A 只读取具体绘画输入。新主体限原创人类角色或非动物器物，不使用动物、拟人动物、兽耳兽尾或动物同伴；画风参考不授权复制其中动物。原画无字无框，宿主排字；不以代码插画、静态海报、旧卡换名或切一张图重复贴层替代真实分层。PNG 仅是素材或静态留图，成品是主 HTML 内的可交互卡。制作路径与动态验收见 [交互闪卡契约](references/interactive-card.md)。

只使用本次可访问且授权的个人信息。未知事实不编造，愿望不写成成果，署名按本次实际总结者，不按历史提到的模型推断。无本轮照片/许可不画本人肖像；可以选择明确不冒充真人的象征形象。

## 工具与审查

首先用当前服务的内置生图，不从环境变量倒推可用性。绘画只表达具体可见形象与一个画风；窄提示与“平台隔离上下文”是不同事实。严格按实际工具接口传递，不使用弃用参数或伪路径，不承诺清除宿主无法控制的上下文。

优先真实独立视觉任务；没有独立任务则允许当前 AI 看实际原件并自检，结果必须注明 self。没有看到图片不能写视觉通过。代码校验不能代替审美判断，供应商 ID 缺失不要求编造。

浏览器检查只在相应工件生成后运行；缺浏览器/缺 WebGL记录未验证，不禁止原型生图。真实功能故障或已知美术不合格仍须修复，不以占位产物交付。

默认命令是 `scripts/portable.py`。旧 `task-card` / `task-site` 保留 strict，不要自动调用后再被其独立审查门禁阻断。参见 [审查标准](REVIEWER.md)。

## 完成边界

完成与审查等级分别报告。自检完成不是“独立审查通过”；生成文件不是“所有浏览器和 GPU 均验证”。只交付当前已检查的目标；有生图但卡片未通过，不偷偷输出无卡阶段包。真正无生图时，无卡 HTML 就是完整目标。

默认私人作品，不公开、不部署、不 push，不导出原始聊天、密钥、内部工作目录或字体文件。平台的授权/安全/肖像要求不能被“一句话”覆盖。

无卡分支也兼容没有视觉查看能力的文本服务：允许真实的源码/结构审查（`source_review_only`），完成 HTML 后如实说明没有视觉验收；这项例外不适用于完整闪卡分支，详见 REVIEWER.md。
