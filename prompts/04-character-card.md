# 从已核对的事实生成专属卡面

依据当前用户已核对的事实写称号、tagline、reflection、关键词和一个主要视觉隐喻。严格模式各项引用本次可发布 fact IDs，字段遵循 analysis schema；不借作者、示例或他人的人格与图像。每张卡固定 SSR，不生成战力或排名。

生图前读取 `references/art-direction.md`，它是画风选择、原型、独立层、验收与有限修复的统一契约。保留用户明确提示与最新修改，AI 补足未指定的设计；写入本次独立美术 brief 并用于实际图像调用。没有授权照片标 original_character，不声称还原本人外貌。

运行 art-brief，生成无字原型，再按实际画布规格直接生成原生独立层；独立排字与同像素线稿按契约执行。实际看图后保留验收记录，generated 不等于 approved。署名取当前 summary_meta，模型版本未知留 null。

继续按 `CARD.md` 装层、校验并交付当前人的分层卡包；不要在原型图片或 brief 阶段结束，不在闪卡流程里构建星图 HTML。
