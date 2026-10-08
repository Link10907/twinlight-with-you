---
name: twinlight-with-you
description: Create a personal Twinlight galaxy HTML with an embedded illustrated SSR card, preserving the approved V10 galaxy, reveal, native-layer parallax and foil. Use for personal Twinlight creation or updates. Uses actual image tools, a real independent visual review task and browser evidence. Platform IDs and OS read-only permissions are optional audit metadata, not prerequisites.
---
# Twinlight · 与你同光

用户一次发起；内部制作、独立审查、有限返工；同一次交付真实成品。默认 `both`：个人星系单文件 HTML + 内嵌同一张原生分层 SSR 闪卡。只要一项时使用 `html` / `card`。不把用户变成审查员，不让用户反复发送“继续”。

## 固定不变的产品基准

保留 V10 星系、靠近才显示的行星、连续双星系交融、署名提问、揭卡、翻面、紧凑层内视差和视角驱动镭射。首页全景用流动光点，选中主体发光，不改成完整行星陈列；交融不超过 15 秒。模板、renderer、shader、音乐不由语言模型重新设计，也不重写模板锁。

默认 `twinlight-collector`：精细原创幻想收藏卡，可信体积与材质、完整环境、明确焦点、前中后景。先实际看随包参考，再设计当前人的一个主体和一个动作。只有用户明确换画风才切换；主体简单不等于画面廉价、空白或剪纸化。原画无字无框，文字与镭射由程序产生。

可复用的是品牌设计，不是别人身份。仅依据当前授权资料；提问不是能力，计划不是成果，助手的夸奖不是用户事实。默认原创概念形象，不冒充本人肖像；实际肖像需本轮照片和授权。称号来自稳定行为，不机械列岗位。署名取实际总结模型，不从历史里猜。

## 执行与权责

先读 [AGENT.md](AGENT.md)；独立审查者读 [REVIEWER.md](REVIEWER.md)。按步骤再读 [CARD.md](CARD.md)、[宿主契约](references/host-contract.md)、[质量工作流](references/quality-workflow.md)，不要一开始把整个目录灌入模型。

生产者做内容、独立图像任务与装配；Reviewer 看实际原件、按固定标准给出 accept / revise / blocked，有否决权；程序校验输入、图层、同版文件、动态证据和审查绑定。生产者不能替自己签字，也不能用同一会话切换角色冒充独立审查。

**预检功能，不把审计要求当成功能要求。** 有真实独立任务且能看图，就执行审查；不要求平台会话 ID、调用 ID、签名回执或 OS 只读权限。缺失 ID 如实留 null，未强制只读留 false；默认用独立任务约束、分开输入包及审查前后文件哈希确认原件未变。`warnings` 与身份未认证不是停止理由。生产者仍不得代签，驳回仍须返工。

先确认真实生图/参考/原生透明编辑/任务隔离与持续执行。WebGL 尚未在预览测试可先为 null，进入动态阶段再实际验证；确认缺少真正必需功能才说明对应缺口，不伪造能力或成品。遵守当前工具接口，不能靠文档激活弃用参数。

## 优先使用实际执行器

先按 [可执行接入](references/execution-adapters.md) 选择已授权路线。`execution.py image` 会真正调用图像接口，`execution.py review` 会真正调用独立视觉模型并绑定裁决；不是只创建 prompt/packet。主宿主不暴露子 Agent 时，可用已配置视觉 API 或全新 Codex CLI 任务，不据此直接宣布不支持。`doctor` 仅查配置，实际探针和生产调用才证明连通性。已有真正的宿主窄任务仍可用，不强制新付费服务。

## 唯一生产链

`功能预检（审计缺项仅说明） → 冻结内容 → 独立无字原型 → 原型审查 → 原生分层 → 合成审查 → 排字与独立动态预览 → final 审查 → 固定 V10 集成 → release 审查 → 导出`

每次图像调用先生成单任务 dispatch，实际只传当前 prompt、对应图片及工具支持的参数。不能传完整“网站 + 闪卡”请求、个人聊天、已失败网页图或其他卡面陈列。网页效果图不是原型，不能裁出小卡继续凑成品。

每图像角色在同一 RUN 最多三次调用预留；改提示或换 CARD 目录不清零。只修失败环节，保留合格素材；原型变更使依赖审查失效。具体回退见 [返工规则](references/recovery-policy.md)。没有真实返回的未知调用不自动重试或捏造回执。

## 完成与交付

`files_built` 仅表示文件齐备；`complete` 要求当前独立审查及全部技术关卡通过；`request_satisfied` 另核验用户明确要求的聊天内交互。三种模式均须 release；纯 HTML 不要求卡片镭射，但不能免审。

只从 public `run` 的当前报告经 `deliver_artifacts.py` 导出。both 主文件必须是 `site-with-card/index.html`，其内嵌卡必须与通过审查的原生层相同。低层 render/build 仅产生候选，不能赋予交付通过状态。导出时重新核验宿主记录、原型/图层审查及 release，防止撤回或修改后继承旧批准。

最终依据实际 `handoff.json` 一起给出卡图、主 HTML、独立互动预览及完整包。PNG 不证明景深，附件不等于站内运行，CSS fallback 不证明镭射；无实测不承诺换个浏览器就成功。默认私人未确认草稿，不自动 push、部署或公开，不携带原始聊天、字体文件、凭证与审查日志。

严格原话追溯读 [来源流程](references/workflow.md)；站内交互读 [平台适配](references/platform-adapters.md)；完整交付读 [交付协议](references/delivery-v2.md)。已有 v2 阻断记录按 [恢复指引](references/resume-v2-blocked.md) 原工作区续跑，不重置个人内容。本包含真实图像/API/独立 CLI 执行适配，但不包含模型服务、账户或凭证；配置已有授权入口后实际调用，不保证首次生图必然合格。
