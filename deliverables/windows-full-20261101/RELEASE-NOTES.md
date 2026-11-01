Sim2Act Windows 本地 CSV 工程预览

完整便携包包含独立 WinForms/WebView2 窗口、私有 Python3.12.10 和四枚原生扩展。原窗口中创建项目、保存合成 CSV、下载原文件、正常关闭并重开后回读已通过 Windows Server2025 实测；同包后台固定 CSV 计算及结果版本30/v1、15/v2另有独立验收。

下载并解压 `Sim2Act-win64-042ab21c4fa9.zip` 到普通可写目录，双击 `Sim2Act/Sim2Act.exe`。需系统已有 .NET Framework4.6.2+ 和 Microsoft WebView2 Runtime；本包不安装系统依赖。输入页面显示的公开合成测试令牌 `public-synthetic-blank-workspace`，点击“连接”。在“创建项目”创建项目，再进入“资源→添加材料”，名称填写练习文件名、类型选csv，核对文本后点击原保存授权按钮。点击已保存材料的“下载文件”，完成状态显示实际exports路径。只使用非敏感练习材料。

验收使用的文本：

```csv
item,amount,quantity
A,10,7
B,20,8
```

保存文本末尾不附加换行时是34字节；原生导出与输入逐字节相等。原窗口正常关闭后重新双击原EXE，项目、材料及原导出保持。确认窗口和后台都完整正常退出后，备份整个`workspace data`（含控制库与启动身份）、`webview-profile`（页面恢复和请求意图状态）及`exports`，再移除解压目录。退出未知或存在残锁时保留目录、数据和日志，不直接删除。

这份预览默认MOCK、合成SQLite，未在本Windows包验收真实模型、正式PG、任意自然目标、大型Cold性能或目标Windows11；UI内创建并运行CSV应用尚未由本轮点击验收。已验结果只覆盖下列准确入口，不称完整产品验收。没有打包任何真实模型凭据。完整包原始manifest的“desktop未执行”是装配阶段历史状态，后续窗口验收单列在WINDOWS-ACCEPTANCE.json，ZIP未重写。

应用源码：`042ab21c4fa9c7e5ba70c4e2877fb7060d962422`。

- 完整构建与后台保存/重开：https://github.com/T1doo/Sim2Act/actions/runs/41325692393
- 独立窗口登录/关闭重开：https://github.com/T1doo/Sim2Act/actions/runs/41328886324
- 实际窗口保存/原生导出/重开：https://github.com/T1doo/Sim2Act/actions/runs/41332996015

包大小19,745,959字节；SHA256：`cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027`。
