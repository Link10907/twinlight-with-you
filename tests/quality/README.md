# 合成质量回归测试

此目录只包含合成身份、纯色测试像素和明确标记 SYNTHETIC 的回执，用于测试程序门禁。它们不是任何人的作品、不是实际模型调用，也不得复制进交付证据。

运行 `python scripts/verify_skill.py --tests --out /path/out/report.json` 或 `python -m unittest discover -s tests/quality -v`。

测试覆盖宿主缺项、任务污染风险、派发篡改、重放、预算、原图保留、独立审查、动态 no-op、纯 HTML 最终审查与回执无损导入。测试数量由实际 runner 输出，不复用旧版测试报告的数字。

`test_card_context.py` 覆盖窄输入/画风编译、附图角色、返工不累积、阶段审查排除手册和履历、项目外真实子进程与失败无占位交付。所有图片和返回都明确为合成材料；本地HTTP/进程测试不调用真实模型。
