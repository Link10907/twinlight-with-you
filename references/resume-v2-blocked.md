# 恢复被 v2 审计门槛阻断的任务

适用：已有独立任务且能看图，但由于缺少只读权限、会话 ID 或平台回执而在生图前退出。

1. 用本版完整包更新 Skill 规则、脚本、测试和 package-manifest；不要删除 outputs、工作区、person.json 或已有星图。已有本地源码改动时先保留副本并对照补丁，不盲目覆盖。
2. 读新的 SKILL.md、AGENT.md、REVIEWER.md；废止旧“无可验证 ID/回执就保持阻断”的规则。无需搭建新服务或修改操作系统权限。
3. 更新现有 host.json 的事实：平台 ID 不可得就 null/省略，未强制只读就 false；独立任务与看图确实可用才填 true。尚未实际测 WebGL 时保留 null。不改个人内容。
4. 用相同 input、workspace、mode 和 host-capabilities 续跑 public run。新的预检应把审计缺项放在 warnings，给出真正下一步；原任务未生图就从 prototype 开始，不能伪造历史图像证据。
5. Reviewer 默认按 packet + 真实独立任务返回 + import --packet --host-capabilities 执行，不创建虚假的 trace。仍需原型/合成/final/release 的实际审查。

通用命令（路径取当前 run-state/已存在文件，不猜）：

```sh
PY ROOT/scripts/preflight.py check --capabilities WORK/host.json --mode both
PY ROOT/scripts/twinlight.py run WORK/person.json --workspace RUN --mode both --host-capabilities WORK/host.json
```

如旧运行有 in-chat 要求、字体/浏览器参数，保留原参数。新预检 `warnings`、`reviewer_identity_authenticated=false` 或 helper 的 `agent_invoked=false` 不等于产品失败；不得再次因为这些字段退出。真正的缺图、错误分层、审查驳回、动态未验仍不能宣布完成。

本修复不追认任何旧卡或旧“通过”，不把当前基础星图升级成完整成品。目标是在同一次恢复任务内真正完成剩余制作与审查。
