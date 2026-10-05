---
name: twinlight-with-you
description: "Create a personal native-layer definition card and fixed-template Twinlight HTML from authorized material. Use for either artifact or one-request delivery of both."
metadata:
  version: "1.5.0"
  template: "Twinlight V10-derived"
  quality_gate: "art-evidence-1"
---

# Twinlight · 与你同光

用户只请求一次，内部自行完成资料、绘画、组装、验收与接入。默认交付独立闪卡与个人单文件 HTML；明确只要其中一个时按该模式执行。不把 JSON、命令或通用查看器交给用户代替成品。

**先是一幅值得看的画，再把它做成闪卡。文件齐全不是作品完成。**

## 路由

- 未取得完整资源：读 [PROMPT.md](PROMPT.md)，在允许目录下载同一实际 commit 的资源，执行 `scripts/bootstrap.py --root <项目目录>` 检查。链接可读不等于项目可执行。
- 开始与续跑：读 [AGENT.md](AGENT.md)。默认 public `run` 管理独立模块与最终 `complete` 状态。
- 美术：只先读 [references/quality-workflow.md](references/quality-workflow.md)。它按需连接美术原则、证据格式及 [CARD.md](CARD.md) 的命令；不要把整套执行手册塞给图像模型。
- HTML：只读 [prompts/html-build.md](prompts/html-build.md)，固定 V10 模板实际构建并通过 `verify-site`，不自写简化页面、不改模板锁过检。
- 严格逐句来源/本人审阅：沿用 [references/workflow.md](references/workflow.md)，不得转 Lite 绕过审阅。

## 不变的边界

只用当前授权材料，区分本人事实、提问、计划、第三方与助手推测。记忆只支持有限印象，不冒充原始聊天证据。署名采用本次实际总结者；不借示例或作者的人物资料。资料充分先完成私人未确认草稿，`draft=true`、`share_allowed=false`；视觉评审不等于本人批准或公开授权。

没有真实生图/原生透明能力时，卡片未完成。保留已成功 HTML，不拿代码几何图、旧坏图、重复海报或静态 SVG 凑完整 SSR。原生主体、背景与前景保持实际全画布，不抠图、裁切、缩放或重摆；文字独立排版。

只在 public `run-report.json` 的 `complete=true` 时称所请求工件完成。`candidate_outputs` 仅是待验预览；`needs_art_evidence`、`needs_art_review`、`art_rejected` 不能改写为完成。局部命令、旧兼容状态机和 `_run_mechanical` 用于诊断，不是绕过交付关口的第二条生产路线。

本地记录能检查文件绑定，不能认证外部模型来源或自动证明好看。真实看图、工具调用与浏览器检查分别记录；未测项照实说明。用户无需再次请求继续或导入。发布另需明确授权。
