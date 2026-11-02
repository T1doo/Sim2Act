# Independent visual-contract source review

Reviewer `/root/frontend_readonly_review`; baseline `19b5a940d381c4163aeb11b9f71ee2c15f892ed0`. Sole source writer remained `/root`. Reviewer read the approved text and actual reference/design images and reviewed the bounded CSS/JS/test diff without writing files.

The reviewer confirmed ordinary-menu288px cap loss, a source-provable sub560px result region around900px, and busy cancellation width change. Typography, square boundaries, original80px idle background and local motion/reduced motion had implementation evidence; actual visual acceptance remained separate. During final menu positioning review, the reviewer additionally reproduced an old-height cap causing a reopened menu to exceed the viewport. That issue was fixed before sealing.

Final reviewer report:

> 本轮最终 diff 可封存：限定范围内无剩余 must-fix。
>
> 已确认测量前清除旧 `maxHeight`，新增两项回归覆盖短窗限高后放大复开。独立执行最终脚本：**38 项通过，未捕获错误 0**；`git diff --check` 通过。
>
> 菜单宽度上限、任务提前切单区、命令状态等宽及复开定位四项均已收口。验证限于源码、CSSOM与受控几何；真实浏览器像素和原生表现仍未验。本轮未修改文件。

This is independent source/CSSOM/controlled geometry review. It is not browser screenshots, actual viewport geometry or Windows acceptance; no browser/CI/model/PG/native execution was performed by the reviewer.
