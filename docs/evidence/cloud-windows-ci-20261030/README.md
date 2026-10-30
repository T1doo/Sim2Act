# Windows CI：实际失败与精确字节修复

第一次精确输入 `99e79653bbaf8d6324f833fb5f62158c89086b41`，实际run [40981407066](https://github.com/T1doo/Sim2Act/actions/runs/40981407066)，job123822091403，约1分08秒后失败。两个原生模块实际import已完成；随后的原严格_qualified在text_software_anchors原件SHA处报Software anchors changed。浏览器、像素、Windows回归未启动，不能计通过。原老分支jobs按条件skipped，不代替新job结果。

原.gitattributes只有*text=auto，源码和资格JSON没有精确字节规则。云端独立用git core.autocrlf=true过滤复现：text_software_anchors.json由Git SHA256 24f26f…4193a变98573e…bc60，共增加143份CRLF；资格JSON及py也被转换。实际失败日志未直接打印Windows文件hash，故这是一条可重复、与报错相符的checkout根因定位，不伪造远端字节实测。

最小修复仅让/src/sim2act/**保留Git原字节（-text），不删文件、不重算Windows变形字节的资格、不改pin或核心检查。142份资格源加锚点与前端共149文件在同core.autocrlf=true过滤条件下逐字节等于Git原件，原_qualified继续通过。新增CI只读诊断会先核checkout对Git原件，不写文件归一化蒙混过关。checkout-eol-before/after.json保留比较及全部摘要。

准备阶段使用公开仓库标准windows-2025、contents:read、现有锁定依赖和原生编译，0真实模型。原一次性标记和15分钟上限保留，无Actions artifact/cache上传。符合[GitHub对公有仓库标准runner免费、日志不计artifact存储的说明](https://docs.github.com/en/billing/concepts/product-billing/github-actions)。父层读回本次实际失败后明确允许修复版必要一次有界重跑；不会rerun旧job造成attempt2跳过，不自动重复未知失败。

first-run.json与压缩日志保留该次结果。后续修复版必须另记完整SHA、run/job和真实终态；Windows Server/Edge不等于用户Windows11/EXE/WebView2，Mock不等于live。未访问用户电脑、绕旧网络/Library拒绝、增加凭据或安全权限、改main或发布Release。
