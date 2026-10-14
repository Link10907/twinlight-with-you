# 宿主内部：确定本次画风

本文件仅用于 AGENT 的上游准备，不作为制卡任务或图像调用的输入。选择步骤内部执行；给 A 的是已确定的绘画数据，不附选择过程说明。

## 选择

画风是启动句末尾的可选附加项。新卡明确指定优先；未指定或只说随机时，默认 mode=random，从全部五种已安装画风中等概率抽一种，不按履历、职业或形象缩小范围，不询问用户是否选择。随机不保证跨作品不重复；同一作品返工和续跑不重抽。

读取 portable.py style-status --workspace WORK 取得实际 id/version。首页名称映射如下；版本以安装资源为准，不编造新画风，不静默退回幻想风。

| 用户称呼 | style.id |
|---|---|
| 现实纪实、电影纪实 | real-life-cinematic |
| 纸绘手作、纸艺叙事 | paper-craft-story |
| 东方幻想绘卷 | eastern-fantasy-scroll |
| 森系自然 | forest-fantasy |
| 幻想典藏、幻想收藏卡 | twinlight-collector |

仅用户明确要求缩小画风范围或按形象适配时，才用 subject_random：保留至少两个候选，并在私人 reason 中记下依据。该模式不是默认，也不能用于重新抽选已开始的作品。未安装的名称不编造 id，不能按字面相似直接映射为另一画风。

宿主写 WORK/style-request.json：version=style-selection-request-1；subject、scene 使用原 card-image-input-1 格式；mode 可省略；明确选择时 style 写 id/version；默认 random 不填缩小后的 candidates；seed 仅用于可复现实验。

新主体限原创人类角色或非动物器物，不使用动物、拟人动物、兽耳兽尾或动物同伴。无授权照片不冒充本人肖像。风格参考不改变形象种类，不能复制参考中的动物。

```sh
python ROOT/scripts/portable.py select-style WORK/style-request.json --workspace WORK
```

选择记录保存在私人 WORK/style-selection.json。既有随机算法和锁定规则保持不变；只改变新作品的默认策略。没有历史记录时不承诺跨会话不重复。

## 交接

命令返回 selected_style、drawing_input 和该风格的 style_reference_images。交给 A 的文件只有 WORK/card-image-input.json，顶层仍为 version、style、subject、scene。

原编译器按 style.id/version 读取 drawing、materials、palette；图像调用只使用编译结果与当前参考。候选、模式、原因、种子和选择记录留在宿主，不转述为绘画要求，不播报选择过程或历史问题。平台自动继承的对话上下文不在脚本控制范围内，不声称实现隔离。

## 续跑

已完成的 HTML 与卡包保持原样，不重新抽签或改写。跨版本续跑仍使用该工作区原先锁定的 commit 与资源包；当前版本未安装的画风不得补回、重映射或换成另一画风，也不得改写旧绑定来继承审查。

同一工作区复用原输入。旧记录已有的 mode、画风和种子不因默认变更而迁移，漏写 mode 的续跑也读取原记录。主体、候选、种子或画风发生改变需新作品；已存在设计、原型或图层时直接沿用，不补做选择。旧动物输入会被新形象约束拒绝，不将已生成的动物卡静默改造成另一个角色。

保留的五套画法与参考、分层、排字和动态渲染不改；形象约束由输入校验、绘画要求与真实视觉审查共同落实，代码校验不等于成图验收。
