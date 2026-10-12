# 视觉与功能审查 · portable 默认

审查对象始终是本次真实文件，不是提示词、计划、示例图或以前的卡。优先可调用的独立视觉任务；没有独立任务时允许当前 AI 对实际图像/页面自检，`method=self`，不能写成独立 Agent 通过。若根本无法查看实际输出，不得填写视觉 accept。

## A：原型、图层与最终卡

原型检查：主体类别、性别呈现/物种和可见特征符合短设定；单一所选画风；画面完整、主体可辨、有材料与空间层次，无网页截图、图表、标题卡框或无关场景。

图层检查：同一原型、同画布、真实透明主体与前景、完整背景、没有重复人影、穿帮裁边或海报多贴层。native_layers 检查原生编辑；assisted_layers 另查真实轮廓、补背景、RGB 保真和 layer-process.json，不将辅助处理写成原生透明生成。真实透视时应呈现前后差；未观察动态就不写已验证。

card 最终检查键：`subject_and_style`、`prototype_consistency`、`native_layers_and_alpha`、`typography_and_attribution`、`composition_and_depth`。须逐项符合并写实际观察；不能只输出通过五次。辅助路径只将 native_layers_and_alpha 换为 assisted_layers_and_alpha，其余检查相同。静态原型不替代分层交互成品。

## B：整站

site 检查键：`content_and_privacy`、`galaxy_navigation`、`ending_and_return`、`same_card_or_no_card`、`layout_and_readability`。无卡版最后两项指没有残留卡位/卡按钮、终章正常结束和页面布局正确，而不是强行检验不存在的卡。

动态检查按 [交互闪卡契约](references/interactive-card.md) 运行当前 HTML，验证拖转/翻面/自动轻摇、触摸、内部视差、文字固定与实际 WebGL 镭射，不以 PNG 或“存在 canvas”代替。无 WebGL 的 CSS 运动只记 limited；无浏览器记未实测；实际失败禁止交付。

浏览器检查与视觉审查分开：资源完整、JS 语法、真实交互、GPU 渲染、离线 file:// 各自记录。可运行的功能检查失败必须修复；无法启动浏览器等记录 unavailable/limited，不伪填 passed。

## 机器记录（宿主写，不是用户表格）

每个 review-card.json / review-site.json 保存 `stage`、程序返回的 `target_sha256`、`method`（independent 或 self）、`verdict`（accept/revise/blocked）、`checks` 对应布尔值、`observations` 实际观察。独立任务另记真实 `execution_ref`；没有平台任务 ID 时说明可观察的任务身份，不生成虚构 ID。

只有 accept 且本阶段检查均符合才续跑。返工后的目标字节改变必须重看，旧批准不能通用。缺能力不是美术失败，自检也不是独立审查；在交付说明里保持这个区别。

默认每角色最多三次真实生图/编辑，记录 WORK/image-attempts.json，复用已合格层；到上限仍不合格就报告具体阻断，不替换成占位品。

strict 模式继续使用 references/strict/REVIEWER.md 及真实独立执行器门禁；portable 不伪造 strict 放行文件。

## 无卡且无视觉能力的文本服务

仅 html-only 允许 `review-site.json` 使用 `method=source`：实际审查源码、内容和结构，不检查不存在的卡，不伪装看过截图。检查键为 `content_and_privacy`、`template_and_assets`、`navigation_code`、`ending_code`、`card_feature_absent`，逐项说明实际读到的结果。已知语法/功能错误仍阻断。

交付标为 `source_review_only`，不称视觉审查通过，`all_checks_passed` 不会为 true。full/A 卡片分支禁止此替代。这样没有图像生成或查看能力的文本 AI 仍可完成 HTML 分支，而不是再次被图像审查门槛卡住。
