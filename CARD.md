# 任务 A · 原生生图与闪卡（portable）

只有自动路由 full 才读取本文件。没有生图能力直接制作无卡 HTML，不生成卡片或卡面提示。默认优先宿主原生工具，不要求外部 API。

## 具体形象 → 一个画风 → 原型

根据真实授权资料凝练为一个具体主体（男性/女性/动物/精灵/具象物件等）、2—5 个可见特征、一个动作、一个主要道具、一个简短场景。选择 `assets/art-styles/image-presets.json` 中一个画风，默认 twinlight-collector。参考素材只作风格，不当当前人物卡层。

上层资料不传入绘画：姓名、履历、职业清单、称号、总结模型、星系、HTML、网页截图、验收手册都排除。只表达可见形象、所选画风和当前构图/图层目标。用实际支持的接口，不虚构 prompt 参数、清空历史能力或附件地址；平台自动继承上下文时注明 contextual_native_tool，不能谎称严格隔离。

原型为 3:4 单幅、无字无框。宿主应先看真实原型，审查明确主体、画风、完整场景、焦点、材料和前中后层次。形象简洁不意味着平面、低细节或 PPT 图形。只让用户在平台要求肖像照片/许可等必要情况参与。

## 以同一通过原型制作原生层

分别调用当前生图/编辑工具，参照同一实际原型取得完整背景、透明主体、透明前景效果；各层保持同画布和位置，背景包含被主体遮住的环境，主体没有另一个不透明背景。不要复制整幅海报伪装多个景深，不以程序画出人物，不把风格参考当作本次图。

当前工具真的不能完成所需原生层时，报告“原生分层工具链受限”，不是“没有生图”。不要无声降成静态卡或无卡版。

程序排字保留原图字节，图像任务不画卡面标题：

```sh
python ROOT/scripts/prepare_card_layers.py --help
# 按真实文件传 --data / --background / --subject / --effects / --prototype / --out 等所需参数。
# 该脚本只排字并装配；不会生图。具体参数以 --help 为准。
```

按 [默认契约](references/portable-contract.md) 保留真实生成记录 WORK/generation.json（原型与三个图层的实际哈希，工具名称、观察和实际隔离等级）。不要求供应商任务 ID，不允许编造调用。记录由 AI 自动完成，不要求用户手填。

```sh
python ROOT/scripts/portable.py run WORK/person.json --workspace WORK --capabilities WORK/capabilities.json --layers WORK/card-task/native/layers.json
```

程序将构建独立预览，再请求针对当前字节的 card 审查。只有 A 通过才继续 B。看真实预览检查排字、边缘、构图和可用动态；无 WebGL不能写镭射已验证。失败仅返工具体图层，每角色最多 3 次真实尝试，同一私人目录保留失败记录。

完整模式严格保留真实原生分层、精细幻想收藏风格和同卡嵌入；portable 只降低基础设施门槛，不允许占位卡冒充成品。显式 strict 另读 references/strict/CARD.md。
