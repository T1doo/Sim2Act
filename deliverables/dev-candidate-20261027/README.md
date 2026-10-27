# Sim2Act 开发交付候选 · 2026-10-27

产品源码：`12c83541c8d0cba82820531517bac8b96de8ca82`。这不是正式发布或整体验收。

- `Sim2Act-preview-win64-12c83541.zip`：18,997,744 字节的 Windows x64 **隔离合成预览**。包含私有 Python 和 21 个已锁定运行依赖；在其原预览范围内不需要用户安装 Python、SDK、编译器、Node 或 PostgreSQL。沿用现有 Edge/UCRT 前提。解压后入口为 `Start-Sim2Act.cmd`，只能使用非敏感合成材料。
- `Sim2Act-local-candidate-12c83541c8d0.zip`：2,410,449 字节的开发源码/wheel 包，含现有安装及装配脚本。它需要开发运行环境，不能冒称免环境成品。
- `delivery-manifest.json`：以上包和清单的完整 SHA256；`candidate-manifest.json` 绑定精确 Git 源码及 wheel；`current-portable-inputs.json` 绑定原运行依赖。旧包和旧输入没有改写。

便携包 SHA256：`82e8bb87bc01148ad1c8e639f6b2aac9b154d40b75d651b9c8e554d47fccd13c`。

**本轮只在 Linux 构建及核对归档，没有运行 Windows、浏览器、Worker 或模型。** 运行库沿用原已冻结、已标记 superseded 的 Python 3.12.10，不能作为长期生产部署。未新增用户电脑执行许可；不要为运行它绕过系统签名、SmartScreen 或沙箱拒绝。

便携入口仍显示合成工程身份、没有真实模型接入或正式发布能力。数据、临时文件及独立浏览器 profile 放在解压目录；系统/浏览器可能产生的 OS 痕迹不能承诺不存在。退出沿原说明 Ctrl+C 一次并等待 `clean:true`，再关闭该预览浏览器，之后才能删除自有解压目录；不要删除在途 claim 或用户数据。

精确构建、定向验证及独审见 [本轮证据](../../docs/evidence/development-delivery-binding-20261027/README.md)。G0仍 UNKNOWN；七族不可变候选未启用，完整容量、消费者闭包和净收益尚未证明；真实账户来源、最新组合 PG/原生/人工语义验收不因本包获得通过。
