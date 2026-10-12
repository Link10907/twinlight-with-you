# 任务 A · 原画与交互闪卡（portable）

只有自动路由 full 才读取本文件。确实没有生图工具直接制作完整无卡 HTML；原生层制作受限不等于没有生图。默认使用宿主工具，不要求外部 API。

## 具体形象 → 一个画风 → 一张冻结原型

根据真实授权资料凝练为一个主体、2—5 个可见特征、一个动作、一个主要道具和简短场景。选择 assets/art-styles/image-presets.json 中一个画风，默认 twinlight-collector。参考素材只作风格，不当当前人物卡层。

绘画输入不含姓名、履历、职业列表、称号、总结模型、星系、HTML 或审查表；仅可见形象、所选画风和当前图层要求。严格使用宿主支持的接口；不虚构 prompt 参数、文件引用或清除历史能力，平台继承上下文时如实记 contextual_native_tool。

原型为 3:4 单幅、无字无框。实际查看主体、画风、场景、材料、前后空间与焦点；通过后冻结文件和 SHA-256。不要每次失败都重画原型或改用户人格。真人肖像仍服从平台照片与许可要求。

## 稳定取得同一套真实图层

先读 [交互闪卡契约](references/interactive-card.md)。文生图、同图引用编辑、透明输出分别检查；未知仅做一次可验证的绑定试验，不假定能力。成功后复用图层；首次换人/换场景就停止相同方式重试。

- native_layers：以同一原型原生生成完整背景、透明主体与前景，沿用 prepare_card_layers.py。
- assisted_layers：原型仍须原生生成；使用实际轮廓分割、补全背景和必要边缘修复。prepare_assisted_layers.py 接受真实蒙版/已通过图层，保留原型像素、同画布和源记录，不自动理解轮廓或生成缺失背景。

两条路径都送入原有六层 manifest 与 V10 renderer，不改卡片接口。辅助路径必须明确标注，不能宣称原生透明生成。无可用分割/修复能力时准确报告，不能把静态卡或无卡页面冒充完成。

宿主维护 WORK/generation.json：沿用原型、真实工具、哈希与观察字段；辅助路径另加 layer_method=assisted_layers 和 assembly_record_file。这个记录不送入绘画工具，也不由用户手填。每角色最多三次真实编辑，见契约中的记录命令。

## 装配、审查、动态交付

运行 portable.py run 并传当前 --layers；程序生成 card-task/card/preview.html 和 front.png。前者是独立交互卡，后者仅为静态留图；不能交付 PNG 就宣布完成。

看实际原型、图层与卡面，检查边缘、背景补全、重复人影、文字及视差露底。card 检查键依路径选择 native_layers_and_alpha 或 assisted_layers_and_alpha，其余审美标准相同。缺陷只返工相关层，不修改放行规则。

浏览器可用时运行 verify_portable_card_browser.py，实测内部视差、WebGL 镭射、拖转、触摸、翻面、归位、自动轻摇与减少动态。无浏览器不写动态通过；CSS 回退不冒充 WebGL 镭射。真实运行故障阻断。

A 通过后 B 嵌入同一组原始图层字节、深度、排版和同一 renderer，保留星系↔闪卡跳转。主 HTML 是最终交互载体，不依赖外部预览。显式 strict 仍读 references/strict/CARD.md，原门禁不放宽。
