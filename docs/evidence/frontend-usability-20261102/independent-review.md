# Independent read-only usability review

Reviewer: `/root/frontend_readonly_review`. Baseline `44dcab97a12904d603c308c6bc27aacbbde826ad`; current small app.js/app.css/targeted-test diff, source bytes bound in `source-manifest.json`. No reviewer product writes, commits or pushes.

Initial review independently checked six keyboard/focus cases in memory and the CSS cascade: the old ArrowUp index was wrong, a coarse 44px declaration needed to beat primary/compact specificity, 18px glyphs remain separate from their labels' hit regions, and long labels retain wrapping. The actual HTML had 38 directly nested checkbox/radio labels, only one with an extra descriptive span; no multi-control layout break was found by source inspection.

The final reviewer report after empty-panel labelling was corrected:

> 最终小 diff 独审通过，无剩余 must-fix。
>
> 已确认 `aria-labelledby` 在空记录早退前设置，空检查面板和已有记录均关联当前选中的 tab；与 `tabIndex=0` 配合正确。
>
> 独立执行最终 `frontend_usability_ui.cjs`：**18 项通过，新增 API 请求 0，未捕获错误 0**；`git diff --check` 通过。测试准确限定为受控 DOM/CSSOM，不等同真实触屏、像素或读屏验收。
>
> 未修改文件，未运行大套件、浏览器、CI、模型或 PG。
