---
name: twinlight-with-you
description: Create a private personal Twinlight HTML with an actually embedded native layered definition card. Use a versioned art style and concrete human, animal or object description; validate real image layers, fixed typography, parallax, foil and current delivery files.
---
# Twinlight · 具体形象与完整交付

一次请求的默认目标是 **原生分层闪卡 + 已内嵌同一卡片的固定 V10 单文件 HTML**，不是两张图片或一个网页效果图。仅明确只要 HTML / 卡片时改用对应模式。用户不承担工具问卷、选参数或内部续跑。

## 只沿这一条链执行

完整同版本资源 → 私人内容 → 一套固定风格 + 一个具体形象 → 无字原型与实际审查 → 三张原生图片层 → 实际合成与独立排字 → 真实视差/闪光检查 → public `run --layers` → 内嵌字节复核 → 成品导出。

先读 `PROMPT.md` 与 `AGENT.md`。绘画只读 `CARD.md` 和 `references/visual-contract.md`；HTML 只读 `prompts/html-build.md`。`art-direction-2` 是当前 public 闪卡入口；旧自由描述只保留诊断用途，不能完成本次原生卡请求。

## 不可替代的分工

**风格**由 `assets/art-styles/catalog.json` 中恰好四套版本化模板选择一套。必须落实到实际提示词和来源记录，不凭文件标题认定用了某种风格。不规定所有人的性别、物种、衣服、月夜或蓝金配色。

**形象**明确种类、具体物种、适用的性别呈现、年龄感、2–5 个可见特征、服装、神情、一个动作，最多一个主要道具。选择依据可来自本次授权资料，但绘画输入只包含具体可见描述。未知长相用原创概念，不冒充本人肖像；本人肖像需当前可用照片和授权。

**词语**分开：`card.keywords` 是卡面文案；`visual_keywords` 由形象字段生成。不得把“拆解、验证、共创”等抽象词直接塞进绘画提示词，也不需要把所有经历变成徽标。

**效果**由真实背景、主体、少量前景及固定文字层与原 renderer 实现。程序可以排字、合成、派生主体轮廓线，但不能用几何占位或剪裁海报代替生图。

## 完成边界

只以当前 `run-report.json` / `delivery-report.json` 的 `complete` 和 `primary_output` 交付。both 模式主文件必须是 `site-with-card/index.html`；基础 `site/index.html` 不算已内嵌结果。用 `scripts/deliver_artifacts.py` 导出，禁止手工替换旧 HTML 的 data URI 后宣称完成。

文件完成、本地浏览器通过、聊天宿主直接预览是三个状态。不能承诺任何账号都能在聊天内运行 HTML。能力不足或返工到达上限时如实交付成功模块，不将 static、空层、截图、候选或未测状态改成成功。

所有个人输出默认私人未确认草稿，不自动 push、部署或公开用户数据。不得携带字体文件。真实生图与具名看图记录不是外部来源认证或本人批准。
