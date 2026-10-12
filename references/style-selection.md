# 宿主内部：确定本次画风

本文件仅用于 AGENT 的上游准备，不作为制卡任务或图像调用的输入。选择步骤内部执行；给 A 的是已确定的绘画数据，不附选择过程说明。

## 选择

沿用已开始的设计。新卡明确指定优先；纯随机用 random；默认 subject_random，由宿主根据具体形象、动作、场景和明确视觉要求保留多个适合的候选，再抽取一种。没有更窄要求时六种都可选。所需 id/version 由 portable.py style-status --workspace WORK 读取。

宿主写 WORK/style-request.json：version=style-selection-request-1；subject、scene 使用原 card-image-input-1 格式；mode 可选；style 可显式指定 id/version；candidates 可选；subject_random 指定候选时用 reason 简短记录依据；seed 仅在需要复现实验时指定。

```sh
python ROOT/scripts/portable.py select-style WORK/style-request.json --workspace WORK
```

选择记录保存在私人 WORK/style-selection.json；本次选择算法、版本、锁定和续跑规则不变。没有历史记录时不承诺跨会话不重复。

## 交接

命令返回已确定的 selected_style、drawing_input 路径和该风格的 style_reference_images，以及运行状态。交给 A 的文件只有 WORK/card-image-input.json，其顶层字段仍为 version、style、subject、scene。

由原有编译器按 style.id/version 读取 drawing、materials、palette，生成本次绘画文字；图像调用使用这份编译结果和当前任务参考图。候选、模式、原因、种子和选择记录保留在宿主内部；选择记录不是绘画指令，不转述为附加画面要求。宿主不在图像调用前播报选择过程或方案比较。平台自动继承的对话上下文不在本脚本控制范围内，不声称实现了隔离。

## 续跑

同一工作区复用原输入。改变主体、候选、种子或画风需新作品；旧版已有设计、原型或图层时直接沿用，不补做选择。预设、参考图、原型与图层提示、排字及动态渲染均沿用现有流程。选择记录只保证输入一致，不等于成图验收。
