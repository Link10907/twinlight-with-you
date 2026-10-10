# Card Handoff 1：任务 A → 任务 B

私人契约，代码位于 `scripts/twinlight_core/card_handoff.py`。不触发生图、不提升作品质量、不认证模型供应商身份。

## 封存前提

`task-card` 完成或 `seal-card --workspace A` 会重新检查：A 是 mode=card；内容与 persona_digest 一致；public run 与 delivery receipt 完成；三个卡片输出存在且字节匹配；原型/合成/final 的真实审查仍有效；art-direction-2；当前独立 card release；runner 实际调用的 card browser 报告及同版 HTML；卡包内解码原图、深度/版式与共享渲染器一致。

私人证据必须在 A 内；独立 review 引用的随包美术参考和审查准则另以 resource_files_sha256 绑定，只允许维护资源白名单，不允许任意外部文件。其他证据必须在 A 内，不能依赖下次会话不存在的外部临时路径。图片、JSON 或报告写了 approved/complete 不够；还会重读实际证据。producer 不能编造这些记录。本地文件绑定不等于安全签名或服务端身份认证。

## 清单字段

`card-handoff.json` 包含 version、persona_digest、原生 layers_file、三个固定 output 路径、所消费私人文件的 files_sha256、随包参考/规则的 resource_files_sha256、renderer、native_card、binding_sha256、private。没有用于绕过门禁的 approved 开关。

`renderer` 包含版本、共享 holo 源码、独立预览外壳和生成逻辑的实际 SHA。card-pack.json 复用 layers-1，补充 renderer 与可选 canvas_mapping；图层始终是实际 data URI。版式/深度和原始字节均核对，不只比较文件名。

## 导入与复验

```sh
python scripts/twinlight.py check-handoff A/card-handoff.json --input person.json
python scripts/twinlight.py task-site person.json --workspace B --card-handoff A/card-handoff.json --host-capabilities host-B.json
```

A/B 分开且不嵌套。导入程序重新 inspect A，与已封存清单逐字段匹配；复制 front/preview/pack **逐字节不改动**。B 自动渲染的主文件另做 decoded layer 和实际 holo renderer 对比。B 导出仍重验 A 与当前 B release。

只改 person.json 主题星内容、不变 name/card/summarizer，不改变 persona_digest，因此无需重画 A。改卡面文本/实际署名或共享渲染器需要新的相关审查。已有未受影响的原生插画可以复用，但不能沿用针对旧预览/旧排字的批准。

## 续跑与迁移限制

默认同一私人 WORK 内保留 A 和 B。当前实现不自动搬迁绝对路径、签名证据或旧 both 到新 A；跨主机迁移需保留真实原始记录，重新绑定可见路径并重验，再生成新清单。不能编辑报告里的 success 或删除驳回来“修复”迁移。

只有可分享 card-pack.json 时可以独立查看，但不能直接作为已验收 A 导入 B。旧卡包缺 renderer 指纹时，使用原原图重新构建当前预览/卡包并执行受影响动态审查，不要求无条件重新生图。

## 出包边界

card-handoff.json、原始工具响应和全部审查依赖留在私人工作区。用户作品 ZIP 仅包含已放行主 HTML、独立预览、正面图、可复用卡包、打开说明及去路径交付清单，不含字体文件或凭证。
