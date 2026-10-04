# Twinlight · 与你同光

每个人得到自己的个人星图 HTML；专属分层闪卡单独制作，完成后按需导入页面。

## 一句话启动

**制作个人 HTML**，复制给 Agent 或有文件/代码工具的网页聊天 AI：

```text
请读取 https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/PROMPT.md，根据你实际了解的我生成个人星图，交付可直接打开的独立单文件 HTML 并预览。
```

**制作独立闪卡**，使用另一条入口：

```text
请读取 https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/CARD.md，根据你实际了解的我制作专属分层闪卡，遵循我的美术提示，自主完善特色画风，交付带真实景深与闪光的完整卡片包和预览。
```

AI 自己整理本次材料、处理技术步骤，文案先由本人核对。HTML 流程不调用生图、不等待闪卡；闪卡流程不编写星系叙事或星图网页。两者通过完成的卡包与人物绑定对接，失败与修改各自处理。每个人的内容、形象与文件分别保存。

HTML 的结果必须是实际 `.html` 文件，图片或 JSON 不能代替。闪卡的结果必须是原生独立图层、清单与便携卡包，另附只展示卡片的互动预览；无需先生成星图，原型图片不能代替。缺少对应工具时如实报告该流程未完成，不能自行改变交付目标。

AI 读不到链接时，可一次提供对应说明或完整 skill 包；无需先安装 skill。已加载项目时说“生成我的个人星图 HTML”或“制作我的专属闪卡”即可按相应流程开始。[离线查看器](https://github.com/Link10907/twinlight-with-you/raw/refs/heads/main/viewer.html) 也有两个独立启动入口；它是可选的手动导入工具，最后可下载个人 HTML，不是个人成品本身。

## 内容、卡图与观看

内容仅依据本次授权材料，问题不写成能力，计划不写成成果；SSR 对所有人固定，不表示排名。美术保留明确提示，AI 自主补足未指定的设计，整幅作品须有辨识度，不能给所有人同一张模板脸或同一只鹿。具体美术与分层契约见 [美术说明](references/art-direction.md)。

页面保留 Twinlight V10 星系、双星交汇与揭卡。这个交汇动效属于页面设计，两个制作流程仍相互独立。没有导入成品卡包时，星系 HTML 可正常打开，页内卡图如实显示占位；导入后使用紧凑层内景深与视角驱动的 foil。

成品 HTML 用现代浏览器直接打开，无需安装 Node.js、Python 或本地服务器。网页内预览取决于宿主工具，HTML 不自动公开。GitHub Pages 只在维护者明确手动发布后作为可选线上入口；较大的通用查看器独立下载，不进入默认 skill ZIP。

## 示例与私人材料隔离

默认使用包不含示例历史、预写人物分析或人物图。不同人的分析、布局和卡图分别保存，不能借用作者或其他人的经历。

- `examples/demo/`：完全虚构的严格模式测试材料。
- `examples/lite/` 与 `examples/generated-demo/`：完全虚构的新人物与原生分层演示，只有明确演示/测试时使用。
- `examples/showcase/`：历史作者个人展示，含真实摘要和少量原话；保留源文件用于历史溯源，**不进入默认包、虚构演示包或通用查看器**。不得据此补全任何用户，也不据代码变更推定新的公开授权。

真人聊天导出、证据、照片、确认收据和运行报告放在忽略提交的私人目录。将 HTML 分享出去也会分享其中的摘要与图像，是否公开由本人决定。详细规则见 [隐私与确认](references/privacy.md)。

## 给维护者和 Agent

操作、schema 和修复步骤放在内部说明中：

| 工作 | 说明 |
|---|---|
| HTML 入口与构建 | [PROMPT.md](PROMPT.md)、[AGENT.md](AGENT.md) |
| 内部内容格式 | [Lite 字段](references/lite-content.md) |
| 独立闪卡执行 | [CARD.md](CARD.md) |
| 严格提取、原话核对与增量更新 | [工作流](references/workflow.md)、[提取规则](references/extraction.md) |
| 原型、独立图层与视觉检查 | [美术契约](references/art-direction.md) |
| 直接预览与平台边界 | [预览说明](references/preview.md) |
| 效果实验、平台入口与分发 | [测试与使用](references/quickstart.md) |

```bash
python scripts/package_skill.py --out outputs/twinlight-with-you.zip
python scripts/package_skill.py --include-demo --out outputs/twinlight-with-you-demo.zip
python -m unittest discover -s tests -v
```

默认 ZIP 只含 skill 与通用资源；演示 ZIP 另加白名单中的虚构数据，始终排除真人 showcase、标准答案、隐藏文件和私人目录。`package-manifest.json` 记录范围和文件哈希。生成新页面需要 Python 3.10+ 与 `requirements.txt`，由 Agent 处理；Node.js 与 Playwright 属于开发检查。

精简模式是经过本人确认的有限印象；严格模式核对源引用与状态。机械校验不证明语义蕴含，也不保证跨模型抽取完全一致。冻结数据与素材后构建才是确定性的。生图不是逐次相同的像素复刻；稳定性来自设定、同一原型、画布锁和验收流程。页面支持 1–8 个主主题，每个 0–8 个话题，不强行凑满。

保留 V10 光点流动、靠近才显行星、选中主体发光；先介绍当前 AI 星系，再以连续的双星系拉扯交融过渡至揭卡；有暂停、跳过与减少动态。卡片是分层视差与观察方向驱动的 foil，不是完整三维人体；本项目没有交付上游 Blender/GLB 流水线。

## License

原创代码采用 MIT；第三方来源见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。软件许可不自动授权个人历史、照片或生成图的再使用。
