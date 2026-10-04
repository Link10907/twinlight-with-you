# 从证据到账本之外的简洁表达

使用已核对的 analysis facts，按 schema 填 themes 和 card 的页面文字。固定模板无需重新写 HTML/CSS。

主星表示真实主题，1–8 个；一般在有证据时 3–6 个，但绝不补齐。主题可以是职业、技能实践、学习探索、兴趣或转折，不能套固定“技术、产品、成长、生活”五章给所有人。主题内 0–8 个可区分的记录簇成为行星。同一主题内的问题/计划仍标为探索/计划，不改成能力。

ID 使用稳定语义 slug，用户改昵称、换语言或新增记录时不改已有 ID。标题 ≤14 字；每段约1–2句；不让卡面和首页充满标签。所有 headline/paragraphs/reflection/topic summary 都有 fact_ids，并且只引用自己所属主题允许的事实。不得引入未入账经历。

明确语气：事实用“记录中你说/你完成过”；解释用“这些记录让我看到/从这几次尝试看”；不做诊断或确定性人格标签。生日、起止时间、实际使用模型不从一般知识推断。

card 只写个性化称号、英文称号、tagline、reflection、关键词与 basis_fact_ids；tagline/reflection/关键词均引用本次可发布事实。SSR 恒定，称号是有限印象而非人格测评。不要写 symbols、visual_style、portrait_mode 或 reference_consent，不读取美术生成提示；这四项仅兼容旧数据，新的设定保存在闪卡目录。

输出完整 analysis JSON 后运行 verify。为本人提供 review.md，原文在本地，公开网页只放脱敏转述。请认真核对“引用蕴含”，不要拿程序通过当成语义通过。
