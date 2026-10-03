# 流程与工件边界

| 阶段 | 输入 → 输出 | 是否含私人原文 | 通过条件 |
|---|---|---|---|
| 规范化 | 明确提供的 JSON → history.json | 是 | 分支有界、角色明确、未知日期不推断 |
| 分块 | history → chunks + manifest | 是 | 字符覆盖完整、片段位置稳定 |
| 提取 | 每块 → chunk-results | 是 | 每条用户消息有事实或排除理由 |
| 消歧 | 候选 → analysis.json | 是 | 冲突不覆盖，事实/提问/计划分离 |
| 叙事 | facts → themes/card | 是 | 公开句子闭合到可发布事实 |
| 审查 | analysis → review.md | 是 | 本人核对理解与公开范围 |
| 生图 | 最小化 brief → 独立图层 | 可能含肖像 | 用户授权，真透明，背景补全，左右检查 |
| 构建 | 冻结数据/图层/许可 → HTML | 只含所选摘要与卡图 | schema/审计/视觉/浏览器通过 |
| 分享 | 明确许可的 release | 是，公开摘要 | 单独用户指令，不自动上线 |

`private/`、`outputs/` 默认不入 Git。外部宿主工作目录可以放在仓库之外。把整个输出 ZIP 发给用户不等于可以把该 ZIP 推入公开 GitHub。

## 分块结果格式

每个 JSON 恰有 `chunk_path`, `chunk_sha256`, `history_digest`, `facts`, `message_dispositions`。事实和处置结构与 analysis schema 一致。引用使用完整消息的绝对字符位置，片段内偏移需加 `segment.start`。

`merge-extractions` 检查所有清单块恰有一个结果、摘要一致、所有用户片段有处置；相同 fact ID 只有语义字段完全相同时合并引用。语义冲突立即失败，不能“最后写入者获胜”。跨块同一消息的 `insufficient_context` 可被具体判断补充，其它矛盾处置需显式修正。合并后清空旧 themes/card，防止旧故事套新证据。

若一条超长消息被分开，下一阶段回读相邻片段/完整消息后再做语义判断。不能凭半句定性。

## 增量版本

保存原始规范化快照、分析、ID 映射和 layout lock（全本地）。新导出独立规范化，按原生消息标识对照；同 ID 内容不同先核查编辑或格式变化。更新整份 ledger 的引用与 hash，不能只把 history_digest 替成新的值。确认旧事实是否仍适用，再重新生成依赖事实的句子和卡图 brief。

程序保证冻结输入的排列和构建可复现，不承诺抽取内容跨模型天然相同。重复运行比较 audit 的新增/删除/未使用/敏感/待确认事实；主题合并和删减应提供人可读 changelog。
