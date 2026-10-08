# 状态、局部返工与终止规则

原则：用户一次请求，内部有限闭环；失败定位到一个对象，不扩大重做范围。完整状态从当前 public run 读取，不能只看进程退出码或文件存在。

| 状态 / 缺陷 | 责任对象 | 下一步 | 必须保留 |
|---|---|---|---|
| capability_blocked | 宿主接入 | 修真实生图/编辑/独立视觉任务能力；缺平台 ID/OS 只读不是此状态 | 已有文字、页面候选、缺口记录 |
| needs_card / needs_art_direction | 当前内容对应的美术任务 | 固定画风、一个主体动作，编译 prototype | 已冻结文案和 persona |
| 网页图、多卡图、错误比例 | prototype 调用边界 | 核对真正传输的任务；同设计重试 | 原始失败图、响应和派发记录 |
| 画风粗糙、材质扁平、焦点混乱 | prototype | 先修绘画，再审，不进入分层 | 画风与个人定义 |
| 切头、双影、背景糊块、坐标漂移 | 对应 native layer | 只重做失败角色 image_edit | 合格原型、其他层 |
| 文字拥挤/错字 | text 排版 | 程序修排字，再 final 审查 | 原画与原生层 |
| dynamic_unverified / foil 无变化 | 浏览器、renderer 运行条件 | 固定视角与时间做 foil/depth 对照 | 合格美术，原始失败截图 |
| needs_art_review / needs_independent_review | Reviewer | 真实独立读图并导入裁决 | 原件不动 |
| art_rejected / release_rejected | blockers 指定对象 | 最多三个具体修复，复核新字节 | 旧审查和通过模块 |
| reviewer_blocked | 缺少真实观察或实际独立任务 | 修实际审查能力，不能生产者代签 | 完整候选与未测说明 |
| needs_release_review | 最终运行页面 | 看同一 HTML，不拿独立预览代替 | 通过原型和分层 |
| 站内入口不支持 | 宿主展示 | 保留已完成文件，明确 request_satisfied=false | 全部文件，不重画 |

## 预算与依赖

每个 prototype/background/subject/effects 在同一 RUN 首次加最多两次修复。`visual_plan dispatch` 在 `RUN/production-attempts.json` **预留调用即计数**，换 CARD 路径、重编译不会清零。没有可靠取消/未调用证明的未知返回不自行减次数；这是保守的成本保护，不是可绕过的“重新开始”。生产只串行派发；锁冲突先检查是否仍有进行中任务，不能并行重复调用。

`visual_plan.py repair` 支持 prototype 和 layers，在同一设计上追加实际可见缺陷；不改人格、风格和已通过构图。结构性换设计不是改两个 hash；需要新原型并使全部依赖层失效，仍受原 RUN 的总角色预算约束。达到上限保留所有成功模块，完整卡保持未完成。

原型变更 → composite/final/release 失效；任一层或排字变化 → composite/final/release 按哈希重验；HTML 变化 → release 和站内观察失效；审查被撤回 → 导出器重新查上游，不继承文件已生成的状态。

## 审查输出

统一 pending / accept / revise / blocked。accept 需要全部必须项通过且 blockers=[]；revise/blocked 需 1–3 个对象明确的缺陷或能力缺口：object、location、evidence、repair，可加 preserve。审美不靠平均分；读不到图不能判通过。

`reviewer import` 默认原样导入已发生的独立任务响应，以 --packet 和 --host-capabilities 绑定原件；不要求 trace 或平台 ID。art 阶段用 `bind-review`；其 revise/blocked 也会成为当前裁决。release 用 `activate` 选择裁决，旧记录归档；activate 不是 complete，必须续跑 public run。没有任何 helper 自动生成 accept。

## 禁止的救场

不能裁网页效果图做卡、粗糙抠图代替原生编辑、复制同海报为多层、背景模糊涂抹代替补全、修改模板锁消除差异、将 CSS fallback 称为镭射通过、把测试合成回执用于真实交付，或通过换目录伪造“第一次尝试”。

不增加无关 Agent 数量；一个生产者、一个独立视觉 Reviewer、程序检查足够表达本流程。审查不应变成改变用户喜好的第二次创作。
