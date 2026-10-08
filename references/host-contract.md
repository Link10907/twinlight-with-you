# 宿主能力契约 · 先查清，后生产

`preflight.py template` 生成 `host-capabilities-2`，全部未知项为 null；不是已连接能力，不会创建 Agent。由当前宿主从实际工具契约与探针结果记录，不要求用户手填。`preflight.py check` 只核验声明一致性，不认证服务商。

## 必须取得的事实

| 范围 | 必须记录 | 不可接受的替代 |
|---|---|---|
| 宿主 | host、真实 producer_session_id | 随手编一个会话名 |
| 图像 | 实际 tool 与 source；image_generation、reference_images、native_transparency、native_image_editing、post_image_continuation | 能生成图片就假设所有编辑能力都有 |
| 文本传输 | prompt_transport=explicit_prompt 或 isolated_task_context | 参数弃用但仍写 prompt；共享完整上下文自动推断 |
| 图片传输 | reference_transport=explicit_attachments 或 isolated_task_context | 在文字里只写文件名、hash 或“已看参考” |
| 原生画布 | 实测 native_canvases；或诚实声明 canvas_selection=prompt_only | 把提示比例说成接口保证；后期裁切修成 3:4 |
| Reviewer | 实际 tool/source；isolated_session、read_only_inputs、visual_inputs、runtime_evidence | 同一会话改角色名、纯文本模型不看图 |
| 运行 | 实际 browser、WebGL 探针/source | 根据 Chrome/Safari 名称推定 shader 可用 |

`prompt_only` 仅是尺寸偏好；返回尺寸仍逐张检查。任务整体执行受到宿主系统规则限制：本包不能让弃用字段生效，也不能让一个结束即返回的生图模式继续组装；需要当前确实可用的持续执行/隔离工具。没有就保持 `capability_blocked`，不反复生成网站海报。

生图与审查的隔离是两件事：前者防止“做网站”的上下文污染插画任务，后者防止生产者给自己签通过。即使工具只允许上下文推断，也只能在真实隔离任务中使用；不能把大量强制提示公开发到聊天后假装隔离完成。

## 使用

能力表放在 `WORK/host.json`，不放进用户最终交付包。首次 public run 用 `--host-capabilities WORK/host.json`；后续可省略，工作区记住来源。修改能力表会触发重新检查，不继承旧通过。编译器可直接接受完整 host 表并取 image 子表。

图像 dispatch 会冻结实际 prompt 文本、参考文件、设计、宿主表哈希与唯一角色。只把 `prompt_text`、真正参考图片和工具支持参数传给生图工具，不把整个 envelope 传入。派发记录、能力表均保留 `provider_input_verified=false` / `host_identity_authenticated=false`。日志一致不等于接口有效输入经过认证。

本版新卡生成需要满足完整能力表；缺少能力仍可构建本地候选。最终三种 mode 均需要独立 Reviewer 与浏览器；html 不依赖生图或卡片 WebGL。站内入口是否满足仍由独立 `host-preview-2` 实测，不因这里的 available 声明而通过。

## 隐私与故障

source 只记录工具能力摘要或不含凭证的说明，不放密钥、令牌、原始聊天。宿主无法取得真实会话或回执标识时准确记录缺口，不创造编号冒充。权限由宿主真实执行，JSON 中的 read_only_inputs=true 不是操作系统权限隔离。

预检受阻时一次说明具体原因与可保留模块，不以“换模型”“重新上传”“再发继续”为默认解决方案。只有用户明确同意才切换需要付费、连接外部服务或上传资料的路线。

CLI compile 未指定 --canvas 时，从已声明的原生尺寸选择最大的有效 3:4 画布；prompt_only 路线只给尺寸偏好，仍检查实际返回。原生分层继续冻结已批准原型的实际画布。
