# 任务 B · V10 主 HTML（portable）

## B0：确定没有生图工具

`portable.py` 路由 html-only 时直接构建。无需 card 字段、不读取绘画提示、不创建任何卡资产或交接单。独立版本化的 galaxy_only 装配投影移除卡片 DOM、导出面板、快捷入口、holo renderer 和揭卡逻辑。保留锁定的原 V10 星系、近景行星、交融与音乐源代码；结尾是继续探索与返回星系。`#card` 不会打开空卡。

不调用旧 `run --mode html` 的 debug-placeholder 路径，也不拿参考图或抽象星盘补卡位。无卡版是此次授权的正式作品，不叫“待补闪卡”。

## B1：A 已通过

从本次 A 读取实际图层。portable.py 校验 persona 绑定、原型/层记录、实际 layer_method 与 A 视觉结论，构建同版 V10 + navigation，再逐一比较内嵌图层原字节、renderer 和图层深度。B 不重新生图、不改变 A 排版，也不读卡片美术设计来重画。

完整剧情与“我的闪卡”入口指向同一个卡片；返回星系保持既有导航逻辑。主 HTML 内嵌图像、脚本、样式和音乐，不依赖旁边的卡预览。最终卡可拖转、翻面、自动轻摇并显示独立层视差；WebGL 可用时保留随视角变化的镭射。PNG 仅作素材或留图，不得替代交互 HTML。A 的 card-runtime.json 与 B 的整站 runtime-check.json 分开记录，不能把单卡检测冒充星系或终章检测。

## 验证与交付

当前 AI 审查内容准确与隐私、星点/阅读/缩放、终章结束与返回、手机布局，full 另查卡片和同卡导航。真实浏览器可用时运行检查；缺 WebGL/file:// 环境如实标注不验证，不把截图注入模式写成离线文件已打开。已知导航/JS 故障必须修复。

当前目标 HTML 哈希与实际观察记录到 review-site.json，再续跑同一 portable 命令。不要向用户提交阶段网页。代码生成与运行验证分别报告。

`portable.py deliver` 最终导出完整 index.html；full 附可交互 card-preview.html / 静态留图 card-front.png / card-pack.json，html-only 不带任何卡文件。默认私人作品，不自动公开。显式严格独立审查模式读 references/strict/HTML.md。

无卡浏览器检查由 `scripts/verify_galaxy_browser.py --html WORK/site/index.html --out WORK/browser-check` 提供。默认实际打开 file://；若环境禁止只能记为 unavailable。`--load-mode injected` 仅作 UI/JS 定位，不能替代离线打开、完整实时交融或 GPU 测试。检查报告不得直接冒充 review-site.json 的视觉观察。

无卡分支也兼容没有视觉查看能力的文本服务：允许真实的源码/结构审查（`source_review_only`），完成 HTML 后如实说明没有视觉验收；这项例外不适用于完整闪卡分支，详见 REVIEWER.md。
