# Portable 能力与工件契约 · 1.1

## 当前会话能力，非品牌能力表

宿主观察真实可调用工具后写 capabilities.json。例子中的状态必须以实际环境改写：

```json
{
  "image": {
    "status": "unknown",
    "reason": "尚未检查当前会话原生工具",
    "context_isolation": "unknown"
  },
  "files": {"status": "unknown"},
  "reviewer": {"mode": "self"},
  "browser": {"status": "unknown"}
}
```

image status：available / unavailable / unknown / temporarily_blocked。缺 API key、没有独立 Agent、不支持 WebGL 均不能映射为 image unavailable。没有工具须有观察原因；未知继续检查；额度/权限/服务故障不要自动无卡降级。

reviewer mode：independent / self / unavailable。自检需要实际观察能力；unavailable 不能被默认替换成一次伪造视觉通过。原生工具若只显示图却无法提供文件字节，具体记录图片回传限制，不能声称已嵌入 HTML。

上下文：explicit_narrow_task 表示真正独立窄调用；contextual_native_tool 表示原生工具可能继承会话、宿主只尽量最小化当前绘画说明；unknown 不等于隔离。不要调用弃用字段以“证明”窄提示。默认只要求可见形象/单一画风的信息最小化；strict 才额外要求真实隔离证据。

## 下载和启动

已有上传包优先。远程入口必须读取同一 commit 的全部资源（可用现有 bootstrap），保留 V10 lock，不把不同版本的 README/脚本拼在一起。网络、代码执行、文件制作分别检查；任何一步缺权限都不能靠文档创建能力。无法打开压缩包不宣称已经理解包内容。

平台安全审批、真实肖像参考、额外费用和运行环境规则优先；不因“一句话”授权购买服务、公开资料或修改 GitHub。

## 新工作区的逐次调用

新 full 工作区启用 [portable-image-tasks-1](portable-image-tasks.md)：预留具体原型/图层任务、登记真实返回与处置、在 A→B 和交付前核对素材去向。采用结果进入原有 generation.json / 图层流程；弃用结果保留原因但不强行交付。普通文档和本地记录不能拦截流程外的全部宿主调用。旧工作区不伪造过去的调用前记录，无卡流程不启用图像任务。

## 真实生成记录

完整方法与动态交付遵循 [交互闪卡契约](interactive-card.md)，仅改变 portable 分层制作路径，原六层接口与 strict 门禁不变。

full 的 generation.json 是宿主实际生图后的本地记录，不是图像输入，也不是可手填的供应商凭证。字段：

- origin 固定 native_image_tool；tool 填真实工具名称。
- prototype_file 为相对此记录的实际原型文件；prototype_sha256 对应该文件。
- prototype_review 为 self/independent，prototype_verdict 为真实 accept，prototype_observations 为实际观察。
- layers_sha256 包含 background/subject/effects 的实际文件哈希；不是程序草绘。layer_method 缺省为 native_layers；assisted_layers 须有 assembly_record_file，并校验原型、实际蒙版、源像素及输出，不冒充原生透明生成。
- context_isolation 为 explicit_narrow_task/contextual_native_tool，记录实际能力。
- verdict 为图层比对的真实结论；layer_observations 写原型一致性与透明边缘的观察。

程序检验字节一致，不认证供应商来源。宿主不能伪造真实调用，也不能把合成测试记录带入生产。

## 运行验证记录

A 使用 verify_portable_card_browser.py 生成 card-runtime.json，绑定当前 preview.html 和对比帧；不能用 PNG 当成动态验收。缺浏览器记 unavailable，不阻断已构建的交互 HTML，但不能称已验证；实际动态失败阻断。辅助与原生方法均使用相同 renderer 和测试，CSS 回退不得标记 WebGL 镭射通过。

WORK/runtime-check.json 针对当前 HTML 写 html_sha256，status 为 passed / limited / unavailable / failed。webgl 与 offline_file_open 分别写 passed / unverified / unavailable / failed；checks 保留真实检查结果。file:// 被策略阻断时可以做注入页面诊断，但它只算 limited，绝不算离线打开通过。语法/JS/导航功能失败须 failed。

产物已完成与全部能力验证通过是不同状态；只有验证确实齐全才能 all_checks_passed=true。缺 WebGL不推导成无生图。不要为满足 passed 修改检测结果或使用其他用户卡片。

## 模式隔离

portable 不写 strict 的 host-capabilities、card-handoff、independent release 等证明文件，不修改旧门禁让它们“通过”。保留原 CLI 兼容；用户显式 strict 才使用它。

完整模式卡片失败不切换 html-only。明确无生图模式才不带卡，也无需第三方服务。多轮重试只由宿主在实际可执行的当前请求内完成；平台强制生图后停止时报告真实能力边界，不能承诺后台继续。

无卡分支也兼容没有视觉查看能力的文本服务：允许真实的源码/结构审查（`source_review_only`），完成 HTML 后如实说明没有视觉验收；这项例外不适用于完整闪卡分支，详见根目录 REVIEWER.md。
