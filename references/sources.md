# 来源与版本

本项目的格式/设计/历史锚点参考于 2026-10-02 核对。链接是溯源，不会在离线页面自动抓取。

- Agent Skills 官方规范：https://agentskills.io/specification 。根 SKILL.md、可选 scripts/references/assets；安装路径由宿主决定。
- OpenAI 导出说明：https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data 。导出方式与可用性会变化；适配器只处理明确的 JSON 结构，不承诺每种账户/版本都提供相同结构。
- Claude 导出说明：https://support.claude.com/en/articles/9450526-export-your-claude-data 。结构兼容性见 extraction.md。
- RuiC Card Skill：https://github.com/HRuiCcc/RuiC-card-skill 。用户指定 demo-after.gif 的紧凑层次效果；网页使用其开源视差/foil 思路与公式，不包含 demo 图片，不声称逐帧复刻或已运行 Blender。
- ChatGPT 公开介绍，2022-11-30：https://openai.com/index/chatgpt/ 。
- GPT-4 发布，2023-03-14：https://openai.com/index/gpt-4-research/ 。
- Claude 3 家族发布，2024-03-04：https://www.anthropic.com/news/claude-3-family 。

`assets/ai-history.json` 只内置上述三个历史锚点，不是2026完整年表、排名或最新模型目录，也不说明某个人当时使用过它们。扩充时逐条记录官方日期与链接；不要根据知识截止时间填“最新”列表。

星系融合是艺术化演绎。继承模板的银河/仙女座文案保留“或许”，不声称必然相撞；页面包含原模板的天文参考入口。若更新具体概率/时间，需重新查原始研究，不能把旧动画当成科学预测。

GitHub REST 权限排障：https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api 。403 `Resource not accessible by integration` 是连接令牌/集成权限不足的信号；账户自身有 push 权限不代表这条连接能写。
