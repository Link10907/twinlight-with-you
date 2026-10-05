# 固定 HTML 执行模块

只消费已校验的当前人内容与已通过美术关口的原生卡包，使用完整项目的固定 V10 模板。不能自行写另一个 React/Canvas 页面，也不能用页面截图代替 HTML。

先允许基础 site/index.html 成功。成品卡到位后，通过相同 public run --layers 构建 site-with-card/index.html，校验模板来源、两份 persona、真实内嵌六层字节和同卡平面图，并跑当前 HTML 浏览器检查。不能通过替换一段 data URI 或仅改 art_status 接入。

both 模式最终 primary_output 必须是 html_with_card；即使基础文件比集成文件先存在，也不交错文件。HTML 中不得含字体文件、聊天原文、工具响应或未授权公开内容。

脚本、纹理、音频、图像在单文件中真实自包含；没有外部服务器也可在现代浏览器打开。真实运行验证与聊天附件预览分开，宿主是否能执行脚本必须单独观察。WebGL/CSS 降级和音频首次需点击等限制照实记录。

完整 public 报告通过后由 deliver_artifacts.py 导出同一份真实文件；未通过则修失败模块并保留独立成功部分。不要更新模板锁、篡改报告或重画已经成功的卡图。
