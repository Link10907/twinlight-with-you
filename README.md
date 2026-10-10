# Twinlight 双任务版 · v10-split-1.0

**一个包、两个任务、一个内嵌闪卡的 V10 主 HTML。** 新入口见 [SKILL.md](SKILL.md) 和 [AGENT.md](AGENT.md)。

A：`task-card` 独立制作与验收卡片，结束时封存私人交接。B：`task-site --card-handoff` 只导入已验收卡片，完成星系、同页跳转与整页放行。B 不再需要图像生成配置，`execution.py doctor/host --mode integrate` 支持 reviewer-only。

实际入口与命令：[CARD.md](CARD.md)、[HTML.md](HTML.md)；[交接协议](references/card-handoff.md)；可复制给模型的两条任务说明：[PROMPT.md](PROMPT.md)。

本版本是执行流程与工程代码改造，不包含任何新的个人卡片作品，也不声称模型服务已经配置。真实生图、独立 Reviewer、WebGL 和完整剧情仍需在可用环境验证；合成回归只验证代码。旧 `run --mode html/card/both` 保留兼容，以下旧说明仅供旧流程维护，不能覆盖上述双任务边界。

---

# Twinlight · 与你同光

> v2.2 实际执行入口：[可执行接入](references/execution-adapters.md)。生图用 `execution.py image`，独立看图用 `execution.py review`；旧 dispatch/packet 仍只准备材料，不能代替调用。

**v10-quality-2.1-portable-review**：保留 V10 星系与揭卡视觉，完善任务隔离、独立审查、局部返工及成品导出。本版是工作流升级，不是重设计页面或替换指定画风。

## 一句话启动

在同一条消息上传完整 ZIP：

> 请使用本次上传的完整 Twinlight skill 包，先读包内 SKILL.md 和 AGENT.md，保留 V10 的星系与揭卡效果、精细幻想收藏卡风格，根据你实际了解的我，一次生成我的定义闪卡和 Twinlight HTML，完成后一起给我看。请先检查实际生图任务隔离和独立审查能力，内部完成审查与必要返工，不以未通过的候选冒充成品。

资料充分就直接制作私人草稿，不需要先填写人物或审美问卷。资料不足不编造；本人肖像需本轮照片与授权，否则采用原创概念形象。所有卡固定 SSR，不是能力评分。总结由哪个模型生成，就用哪个模型署名。

需要聊天内交互时补充：“请在当前聊天内展示可操作的星系和揭卡，下载附件不能算满足这个要求。”文件完成与站内体验分别核验。只要一个模块时明确“只生成星图 HTML”或“只生成闪卡”。

## 本版具体改进

生图前先查 prompt 是否真能发送、参考图是否真正传入、透明编辑与持续执行是否可用；一张原型是单独图像任务，不把整条“网站 + 闪卡”请求丢给图像模型。

一个生产者与一个真实独立视觉 Reviewer 配合；模型可相同，会话必须隔离。原型、合成、独立卡和最终 HTML 分别审查；三种模式均有最终放行，纯 HTML 不强加卡片镭射。

每个图像角色在同一 RUN 最多三次调用预留，换目录或重编译不清零。只修失败环节，保留已通过素材。错误类型图、粗糙抠图、重复海报不能作为降级成品。

宿主能力、派发任务、原始图像、审查裁决与最终字节相互绑定；导出前重新检查上游审查，防止旧批准被错误继承。pending、revise、blocked 都不是成功。

## 能力边界

完整制作需要可写文件、Python 与依赖、真正可隔离的图像任务、原生编辑透明输出、实际独立视觉审查会话、浏览器及卡片 WebGL。ZIP 包含资源和程序，**不包含已经启动的 Agent 服务**，也不能给宿主补出原本没有的工具。

缺少能力时尽早报告具体缺口，保留可独立完成的文字、页面与候选。不能通过同一对话换角色名来代审，不能靠弃用的图像 prompt 字段强制传参，也不宣称换成某个浏览器就一定恢复镭射。用户不应负责反复发现这些问题。

最终 HTML 为自包含文件；用户打开成品不需要 Python、Node.js 或服务器。站内是否允许脚本执行取决于真实入口，不由附件链接保证。未公开、未 push、未部署；分享文件会同时分享其中的摘要与图像，公开由本人决定。

## 文件导航

| 用途 | 入口 |
|---|---|
| 最小执行规则 | [SKILL.md](SKILL.md) |
| 完整一次请求流程 | [AGENT.md](AGENT.md) |
| 独立任务审查与产物绑定 | [REVIEWER.md](REVIEWER.md) |
| 指定画风、原型、原生分层 | [CARD.md](CARD.md) |
| 实际工具能力与隔离 | [宿主契约](references/host-contract.md) |
| 失败定位、预算与失效 | [返工规则](references/recovery-policy.md) |
| 画面质量判据 | [质量工作流](references/quality-workflow.md) |
| 最终文件与站内体验 | [交付协议](references/delivery-v2.md) |
| 逐句来源追溯 | [严格工作流](references/workflow.md) |
| 本次代码变更 | [CHANGELOG.md](CHANGELOG.md) |

## 核验与分发

```sh
python scripts/verify_skill.py --tests --out /path/out/skill-verification.json
python scripts/package_skill.py --out /path/out/twinlight-with-you.zip
```

默认包包含固定模板、通用无字品牌参考、生产代码和 `tests/quality` 合成回归测试，不带作者经历、真实人物成品、原始聊天、字体文件或凭证。测试结果证明校验逻辑，不证明当前宿主已连接 Reviewer 或新卡艺术效果已经验收。

包内资源清单与 V10 模板锁分别校验。已上传完整包时以包内同版内容为准；不混读远端 main。低层 render/build 命令仅用于诊断，默认 public run 的完整性要求不能借此绕过。旧版没有 dispatch / host contract 的工作区不会自动升格通过；保留旧成果及未验证说明。

原创代码 MIT，第三方来源见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。许可不授权复用个人经历、肖像或其他人的成品。

## v2.1 宿主兼容修复

默认独立任务能看图即可进入审查；平台会话/调用 ID、签名回执、OS 只读权限是可选审计信息，不再阻断制作。原件与 packet 的前后哈希核对、美术否决、原生分层和动态验收保持不变。此前 v2 在预检退出的任务按 [恢复指引](references/resume-v2-blocked.md) 复用原工作区续跑。此修复没有部署 Reviewer 服务，也不是一张新卡已验收的声明。
