# 成品、内嵌和预览的三个状态

`complete` 指本次请求文件、v2具体形象美术记录、原生卡内嵌、实际本地浏览器关口全部通过；不代表外部生成来源认证、不代表本人批准，更不代表聊天宿主一定能运行 HTML。

both 的 primary_output 固定来自 html_with_card；原型、基础 HTML 和 candidate_outputs 都不能顶替。导出器根据当前 public receipt 复核实际文件 hash，仅复制最终 HTML、正面图、独立预览、便携卡包和简短说明。不要把字体、聊天原文、工具响应或内网地址放进交付包。

聊天内预览未知时默认 not_tested。只有实际打开这份文件并观察交互，才可填写 hash 绑定的 host-preview-1，status=available/unsupported/blocked、html_sha256、observation。宿主观察仍是具名事实，不是平台认证；下载成功不等于 available，本地 Playwright 截图也不能替代这个观察。

浏览器检查固定 V10 页面载入、星系浏览、交汇、揭卡和返回；独立卡片检查原生视差、关 foil 对照、零 depth 对照、视角 foil、固定文字、真实拖动、触摸、键盘与减少动态。CSS fallback 可用于可见性和交互，但不算 WebGL foil 通过。

浏览器或图片能力缺失时保留文件和准确未测试状态；宿主预览受限时返回可在现代浏览器打开的自包含 HTML，并可附真实静态截图，不能生一张“网页效果图”冒充运行截图。不自动部署任何用户私有内容。
