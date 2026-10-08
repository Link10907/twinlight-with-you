# 宿主能力：先确认可执行任务，认证信息不作生产门槛

`preflight.py template` 创建 `host-capabilities-2` 的待填写表。表名保留兼容旧工作区，v2.1 改变的是判定语义。宿主从当前工具接口与实际观察填写事实，不要求用户填问卷，不虚构能力。

## 功能与审计分开

| 范围 | 生产所需 | 不应导致拒绝启动 |
|---|---|---|
| 图像 | 实际生成、真实参考传入、原生透明编辑、单任务隔离、返回后可继续执行 | 服务商不暴露 call_id/artifact_id |
| 独立审查 | 实际独立任务、视觉输入、当前候选与参考 | 缺少生产/审查 session ID、签名回执、OS 只读权限 |
| 浏览器 | 可调用浏览器与来源说明；预览阶段实测 | 尚未构建预览时 WebGL 为 null |
| 完整放行 | 真实美术裁决、当前图层/HTML、必要浏览器与动态证据 | 身份未经过服务商认证这一事实本身 |

`reviewer.isolated_session=true` 表示实际可用独立任务上下文，不要求得到平台会话编号。`visual_inputs=true` 必须能看图。不能用同会话角色扮演、换 observer 名字或纯文本复述代替。

`producer_session_id` 无法获取时为 null/省略；`reviewer.read_only_inputs=false` 表示没有 OS 强制只读，仍可通过独立任务的“不改源文件”约束和 packet 前后哈希检查执行审查。`runtime_evidence` 可先留 null，到 final/release 必须实际给出证据。不能把 false/null 改成 true 消除警告。

`runtime.webgl=null` 表示等待真实预览测试，预检返回 deferred_checks，不因“未测试”阻止第一张原型。若已经实测 WebGL 不可用，修实际浏览器问题；不能称正常可用，也不能拿 CSS fallback 冒充完整镭射。完整放行始终依据最终目标的实际动态验证，不依据能力表承诺。

图像传输仍必须是实际有效 prompt 或真实隔离任务上下文；参考图需真实附件/有效图像输入。共享整条“网页+闪卡”上下文、弃用 prompt 参数、只写本地图片路径但不传图，不算支持。native_canvases 记录真实接口尺寸；prompt_only 仅为尺寸偏好，返回仍检查，不后期裁成竖图。

## 调用和结果

```sh
PY ROOT/scripts/preflight.py template --out WORK/host.json
# 宿主据实际接口填写，不按示例伪造。已有 host.json 只更新事实，保留已有内容与 run。
PY ROOT/scripts/preflight.py check --capabilities WORK/host.json --mode both
```

`ok=true` / `may_start_image_calls=true` 只允许进入生产，不等于作品完成。`warnings` 是审计信息不足，不能按 gaps 处理。`deferred_checks` 是后续必须实测的项目，不先编一个成功探针。`host_identity_authenticated=false` 不是产品失败理由。

新增可执行入口 `execution.py image/review` 见 [接入说明](execution-adapters.md)，由其实际请求和原样响应形成绑定。没有主宿主内置子 Agent 时可选择已授权 API/CLI。下述是原生宿主兼容路线。

默认 Reviewer 走 [REVIEWER.md](../REVIEWER.md) 的 packet + 实际独立任务返回 + 无 trace 导入。helper 自己不创建 Agent，因此 agent_invoked=false 正常。不要把本地文件哈希叫作平台会话 ID，不要要求宿主为了运行本 Skill 新建认证服务。

图像 dispatch 仍在真实调用前冻结 prompt、参考、角色及预算。`visual_plan.py record` 的 provider call_id/artifact_id 可省略：脚本会生成带 `local-call:` / `local-artifact:` 前缀的本地字节绑定，并明确 provider_*_id=null。这不是平台回执。实际原始图像和非空的真实返回消息/附件记录仍须保存；未知调用、没有输出、程序绘图不能冒充生图。

## 恢复与隐私

保留 v2 已有 WORK/person.json、RUN 和 V10 页面候选；旧报告因新代码重新检查，重新运行相同 public 命令，不重建人格、不删 outputs。不追补从未发生的图像或审查调用。详细见 [恢复被 v2 阻断的任务](resume-v2-blocked.md)。

不收集密钥、原始聊天或多余用户数据来“认证”审查者，不自动安装服务/调用付费 API/公开文件。只有真正缺少生图、编辑、独立视觉审查或浏览器等功能才说明具体缺口；不能因缺少平台管理能力交付空结果。
