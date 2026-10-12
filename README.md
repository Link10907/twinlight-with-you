# Twinlight 双任务版 · v10-split-1.1

**一个工具包，两个制作任务，一个内嵌动态闪卡的 V10 主 HTML。**

先读 [SKILL.md](SKILL.md) 和 [AGENT.md](AGENT.md)，再只加载当前任务入口。

| 任务 | 入口 | 完成条件 |
|---|---|---|
| A：闪卡 | [CARD.md](CARD.md) | 原型、原生图层、程序排字、互动卡；真实独立审查后封存私人交接 |
| B：整站 | [HTML.md](HTML.md) | 导入已验收同卡，保留 V10；页内切换、完整剧情和独立整页验收 |

## 本次修复

`card-input.json` 是称号、文字和归属，不是绘画提示。绘画只使用 [card-image-input-1](references/card-input-contract.md)：主体类别、物种/性别呈现、2–5个外观特征、服装表情、一个动作和主要道具，另加选定画风与简短场景。程序拼装实际短提示，不追加上层履历、选型理由、偏好长文或整站需求。

原型一次单图；原生图层每次只参照同一已审查原型。实际请求与附件在 dispatch 复核，改写提示后重算哈希仍不能绕过白名单。返工只发当前一句缺陷，历史留在私人记录。

审查按阶段投影形象、画风和实际图片；仅动态阶段加冻结文字与运行证据。卡片审查不读网页手册，集成审查不重新设计角色。错误主体、无关场景、网页拼贴、占位图、错层和缺动态证据不得放行。

A 失败不输出占位整站。旧 `both` 缺卡不再构建 HTML；`lite-build` 缺少图像默认阻断，只有明确调试时使用 `--debug-placeholder`。所有正式卡片导出再次核对实际卡包、渲染器和内嵌字节。

## 使用与验收

[两条可复制任务指令](PROMPT.md) · [执行接入](references/execution-adapters.md) · [审查规范](REVIEWER.md) · [工件交接](references/card-handoff.md)

```sh
python scripts/verify_skill.py --tests --out /path/out/skill-verification.json
python scripts/package_skill.py --out /path/out/twinlight-with-you.zip
```

原 V10 核心、导航、shader、音乐与已有美术参考不变。本包不含新个人作品、字体、原始聊天、账号、凭证或已启动的模型服务。

真实图像调用、独立视觉任务和 WebGL 浏览器能力需要实际环境提供。项目外临时目录不是 OS 沙箱，文件哈希不是供应商认证，短提示不能保证模型每次遵循形象。合成回归只验证程序行为，不作为艺术验收或独立 Reviewer 的替代。

默认私人草稿，不自动公开、部署或 push。任务 B 的主 HTML 自包含；聊天附件预览、本地离线打开与动态效果分别实测，不能相互冒充。
