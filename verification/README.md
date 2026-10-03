# 本次本地验证

66 项 Python 回归通过；21 项浏览器状态、交互、布局与 CSS 分层降级检查通过。1 主星/0 行星、8 主星/64 行星两组容量用例通过。编译 JS 通过 Node 语法检查。

当前 Chromium 没有启用 WebGL，故没有验证实际 GPU 粒子、GLSL 编译或 GPU 卡面像素视差。不能把 CSS 检查算成 WebGL 检查。浏览器脚本在支持 WebGL 的环境会执行关 foil 的像素差检查；`--require-webgl` 会对缺少完整渲染路径报错。

这些是虚构数据的程序测试，不是语义准确率评估。Safari、手机真机和真实用户逐条标注仍未验证。

`unit-tests.txt` / `browser-report.json` / `capacity.json` 为实际运行记录，`summary.json` 汇总范围。远程 GitHub 写入返回403，仓库没有产生本次提交，GitHub Actions尚未运行。
