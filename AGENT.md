# 一次请求执行入口

宿主做三件事：理解当前资料、调用真实图像工具、实际看成品。程序完成模板组装、提示编译、原图记录、排字、验证与导出。不要把整个手册发送给图像模型。

下文 `PY` 指当前可用 Python 3.10+，`ROOT` 指完整 skill 目录，`RUN` / `CARD` 指当前人的私人输出目录。命令由宿主执行。沿同一工作区的 `next_action.resume` 续跑，已成功模块不重做。

## 1. 固定资源和当前内容

运行 `PY ROOT/scripts/bootstrap.py --root ROOT`。只有 URL 时先取得 bootstrap，再用 `--out` 获取同一 commit 的完整资源。下载失败先用当前可用的完整离线包或已有完整仓库重查；缺模板、品牌参考或执行依赖就先修资源。无法取得完整资源时保留资料和真实已有成品，不手写一个“候选 HTML”绕过模板，也不以代码绘画替代图像工具。完整基准见 [V10 品质标准](references/quality-workflow.md)。

读取 `references/lite-content.md`，仅从当前授权资料写 `person.json`。资料足够就做私人草稿；不为了填满页面补经历。记录实际总结者，未知型号留空。明确要求来源追溯的材料使用 `references/workflow.md`，不转换成 Lite 绕过来源审核。

```sh
PY ROOT/scripts/twinlight.py run person.json --workspace RUN --mode both
```

保存真实 `persona_digest`、字体状态、输出路径与 `next_action`。同一工作区内不改已冻结的文案、主人或模式。基础 `site/index.html` 可以先成功，它只是中间产物；both 的目标仍是已接入卡片的页面。

## 2. 用品牌参考完成当前人的卡

按 [CARD.md](CARD.md) 执行。没有明确换画风请求时，使用 `twinlight-collector` 和其随包 `style_only` 参考；不随机从四个无关美术方向中挑一个。画面题材由当前资料决定，参考只提供绘画完成度和视觉语言。

| public 状态 | 下一步 |
|---|---|
| `needs_card` / `needs_art_direction` | 写一个具体画面，编译 `art-direction-2`；不要改人物文案 |
| `needs_art_evidence` | 执行缺失的真实图像任务，登记实际返回 |
| `needs_art_review` | 打开指定的当前图像或预览，填写实际观察 |
| `art_rejected` | 按具体缺陷修失败原型或失败层，保留其余合格素材 |
| `dynamic_unverified` | 检查浏览器和 renderer；文件存在不等于动态通过 |
| `partial_success` / `failed` | 处理报告指出的模块，继续其他独立待办 |

原型先通过审美关，再投入分层；分层只参考当前原型作图像工具原生编辑，保留画布与尺度，不再同时传入其他人物的品牌示范图重新创作主角。主角简单是指视觉主线清楚，不是把画面改成平面图标、稀疏剪纸或廉价模型。每角色最多三次真实返回，失败记录保留；达到上限仍不合格，就准确报告未完成，不用坏图占位凑成功。

## 3. 同一次运行接入成品卡

```sh
PY ROOT/scripts/twinlight.py run person.json --workspace RUN --mode both --layers CARD/layers.json
```

优先执行报告实际给出的 `next_action.resume`，保留字体、brief、浏览器参数。首次续跑会写当前 `RUN/card/front.png` 与 `preview.html` 候选；按 CARD 的 final review 实际检查这两个文件并绑定，再续跑。不能拿另一预览的观察换哈希继承批准。

public run 验证原生层、当前美术观察、模板来源、真实卡片和整页浏览器，再比较最终 HTML 内嵌的六层字节、平面预览与 persona。both 的主文件必须来自 `html_with_card`。禁止手工替换旧 HTML 的 data URI 或更新模板锁来绕过差异。

除脚本检查外，实际看最终页面的首页、进入行星、双星系交融、提问、揭卡和返回。揭卡要看到同一张通过审美的卡，不能只证明页面能加载。视觉观察要点见 `references/quality-workflow.md`。

## 4. 导出并展示同一份文件

```sh
PY ROOT/scripts/deliver_artifacts.py --workspace RUN --out DELIVERY
```

导出到独立空目录，只接受当前 `complete=true` 的 public 报告。给用户真实 HTML、正面卡图、独立互动预览和便携卡包；打开实际成品并附真实预览，不生一张网页效果图替代运行结果。

完成消息区分：文件完成、本地动态验证、聊天内预览。`host-preview.json` 只记本次对相同文件的实际观察，未知为 `not_tested`；宿主不能执行附件 HTML 时，交付可在现代浏览器打开的单文件。具体格式见 `references/delivery-v2.md`。

默认 `draft=true / share_allowed=false`。内容核对、美术观察和公开授权是不同状态；不自动 push、部署、公开个人资料。未完成结果可明确交付成功模块和真实候选预览，不能使用 complete 导出器伪装完成。
