# 准确提取，而不是包装记忆

## 支持的输入

ChatGPT：JSON 数组（或 conversations 数组），conversation 有 id/conversation_id、mapping、current_node。默认沿 current_node 回溯；根消息可以为空。无法唯一确定末端时失败，不任意选分支。显式 `--branches all` 才读取所有分支，并标记尚未消歧。

Claude：JSON 数组（或 conversations 数组），会话 uuid/id、chat_messages；消息 uuid/id、sender、created_at、content 文本块或 text。检测到 parent_message_uuid 分叉时默认失败；显式 all 后需人工消歧。这不是对所有 Claude 导出版本的兼容承诺。

Generic：`{"messages":[{"id":"m1","conversation_id":"c1","role":"user","text":"原始文本","timestamp":null,"platform":"provided"}]}`。文本应是真实可见消息，不是模型生成的“仿聊天”。role 可为 user/assistant/system/tool，human 规范化为 user。日期必须带时区或为 Unix 秒；不能猜时区。

ZIP、Markdown、数据库、截图、附件不在当前 CLI 自动适配范围。可用宿主文件工具读出明确消息后转为 generic；不可恢复的部分写进覆盖限制。不要用 OCR 得到的可疑引文冒充已核对原话。当前程序不会分析非文本块。

## 六种常见误读

| 原文例子 | 应记录 | 不可写成 |
|---|---|---|
| “怎么部署 K8s？” | question / uncertain | 熟练掌握 Kubernetes |
| “我准备学吉他” | plan / planned | 吉他演奏者 |
| “帮候选人写一份医生 JD” | third_party 或任务需求 | 本人是医生 |
| “假设我是 CTO” | hypothetical | 本人任 CTO |
| 助手说“你很有领导力” | 不作为个人事实证据 | 领导力突出 |
| “上次说错了，我已经换工作” | 明确更新，保留被替代记录 | 把两份现职一起写进去 |

只引用 user 不足以排除用户在粘贴别人的话，必须同时分析 speech_context。对真实性无法独立验证的经历，写成用户自述，不当作外部查证结果。

## 引用与覆盖

偏移按 Python Unicode code point，左闭右开；不是 UTF-8 字节、不是 JS UTF-16 下标。读取完整 normalized 消息，使用 `anchor()` 或精确字符串定位。多个相同片段用明确 occurrence。不能改写标点再称为原话。

每条用户消息都要进入 `message_dispositions`。排除也需理由，不能为了“看起来完整”一概标 not_personal。coverage 和 manifest 表示材料处理覆盖，不证明整个平台所有历史均已导出，也不证明语义无遗漏。

## 消歧和时间

事实分 achievement/practice/interest/preference/question/plan/self_description。过去成果用 past，计划 planned，含糊材料 uncertain + needs_confirmation。只以明确新陈述 supersedes 旧记录，不按最近日期自动覆盖不同语义。

事件发生时间与消息时间分离：这版网页 period 只标“记录日期”。“上周”不自动生成精确某一天。“用了很多年”不能变成起始年月。未证实职业、医疗、收入、第三方身份等不进入卡面。

## 人物理解

主题名与卡名是创作，不是假装测出一种稳定人格。跨多条独立证据出现的行为模式更可信；单次经历只能支持“这次/从这些记录看”的有限判断。用具体行为传达情绪价值，避免天才、冠军、胜过他人和心理诊断。

## 测量方案

本仓库回归用例只验证程序约束。正式语义评估应抽样双人标注：本人归属 precision、计划/成果混淆率、逐条引用蕴含准确率、相关事实 recall、覆盖遗漏率、敏感泄露数、纠错保留率。分别按年份/会话长度/文本格式报告，不拿“脚本全绿”代替这些指标。
