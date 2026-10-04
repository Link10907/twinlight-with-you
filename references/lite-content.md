# Lite 内容格式

写 `twinlight.json` 时读取本文件。它是 HTML 构建的内部输入，不是最终交付；最终文件与执行步骤见 `AGENT.md`。

card 字段是页内身份文字，也是显式导入闪卡时的内容绑定；它不要求执行生图。

把下面的结构写入本次工作目录的 `twinlight.json`，供校验与 HTML 构建使用；`intro` 可省略，其余按 schema 保留。每个值都由本次资料生成，使用 `schemas/lite.schema.json` 核对，不读取示例人格。只写页面文字，不添加美术提示；JSON 不是结束条件，不要求用户手写或复制内部数据。

```json
{
  "twinlight": "lite-1",
  "name": "用户昵称",
  "summarizer": "本次实际总结者",
  "intro": "一句开场白",
  "themes": [
    {
      "label": "主题名",
      "english": "THEME NAME",
      "headline": "主题的一句标题",
      "story": ["一段具体叙事"],
      "reflection": "一句寄语",
      "topics": [
        { "label": "话题名", "summary": "有限范围的描述", "basis": "once" }
      ]
    }
  ],
  "card": {
    "title": "专属卡片称号",
    "english_title": "CARD TITLE",
    "keywords": ["关键词一", "关键词二", "关键词三"],
    "tagline": "一句具体的标语",
    "reflection": "卡片背面想对用户说的话"
  }
}
```

| 字段 | 要求 |
|---|---|
| `twinlight` | 固定 `"lite-1"` |
| `name` / `summarizer` | 1–16 / 1–24 字 |
| `intro` | 可省略，最多 60 字 |
| `themes` / `topics` | 1–8 个主题 / 每主题 0–8 个话题；同范围 label 不重名 |
| 主题 `label` / `english` | 最多 8 / 32 字；英文只用英文、数字、空格与半角符号 |
| `headline` / `reflection` | 最多 60 / 120 字 |
| `story` | 1–3 段，每段最多 300 字 |
| 话题 `label` / `summary` | 最多 12 / 160 字 |
| `basis` | `often`、`once`、`inferred` |
| `card.title` / `english_title` | 2–8 / 最多 28 字；英文只用英文与半角符号 |
| `card.keywords` | 3–5 个，每个最多 6 字 |
| `card.tagline` / `reflection` | 最多 30 / 100 字 |

字数按 Unicode 字符计。校验返回修复提示时，只改指出的位置，重新校验完整 JSON；不要换掉已经确认的经历。
