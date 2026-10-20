冻结报告补丁独审通过，P1/P2 均无。runner SHA256 `da3a6f68c30bb8b8077f153762eec38e94ba05d48201b4bb6157e861f805e081`；test `572b66a0b91e231fc0d0cdfdc0624df82fae7e8266257d07580ddd642eb559c8`；workflow `2a7bd3fdbec95eacf52fcf1ffff66f5bd3d95cacc53a79c4535a49e52b000c31` 未变。

清理/脱敏/all-file digest 门均在任何 bundle 之前。先完整计划所有文件，核心和 fixture 回执优先且超限零输出拒绝；可选附件整文件选入或显式 OMITTED_ENVELOPE_LIMIT，保留原 bytes/SHA256/compressed_bytes、chunks0。尾 manifest 覆盖全部候选，EXPORT_SUMMARY 明示 PARTIAL_OPTIONAL_OMISSIONS。保持原 2,000,000 字节 gzip payload 上限；base64、JSON framing、manifest、重复 RESULT 属额外输出，不能将此表述为总 stdout 不超过2MB。

作者实际本地原件为10P/0F/0E/0S、3.671秒，新增两项分别覆盖核心优先/大可选附件明确遗漏、核心超限零输出拒绝。本独审只读源码和原件，未补跑。

原 run39369709238 的真实10P80.318秒、重启hook执行控制流、清理PASS及报告失败事实不变；213+238=451秒。19份原件缺失不能恢复，包括完整SQLversion/restart原件。本补丁仅本地验证，未经Windows/PG运行；不得第三次CI。
