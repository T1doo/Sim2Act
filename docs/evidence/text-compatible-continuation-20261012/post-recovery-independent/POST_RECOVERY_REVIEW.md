# 恢复后的精确文件桥核验

**PASS，仅核验既有证据和当前源码；没有新增测试或重跑任何 probe。** 当前待提交代码精确对应既有最终80及root249证据所指的冻结版本。root为唯一仓库写者，本追加只写独立/tmp/text-continuation-post-recovery-bridge-20261012，未改原80报告、manifest或历史原字节。

实际Git HEAD为 df5f422174c4eeea96e5dd16c141dc0a4b36b3e6，branch dev/text-compatible-continuation-20261012；这是当前未提交候选的base，不能冒充最终commit SHA。

- 401 src/tests完整映射当前逐文件一致，指纹3bb07485d301ea8b01bd4e2b408e71b4789650934ebf8b1734dafc66ff08a32f。
- 当前67Python（config除外）实现指纹c0cdc4e98de6a043bb43f1b1d5b27d4b57f525164922fb65cf70173f3b1d2a93，pyproject指纹49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81，两者精确一致。
- 独审21文件快照的记录hash与snapshot自身原字节全部一致；其中20份代码/json/web/pyproject也与live源码全部一致。1份合同文档不作为代码资格条件，此次当前文档也未出现差异；后续root更新文档不改变此代码桥结论。
- FINAL_REVIEW与原manifest列出的101份当前80产物逐hash一致；history-manifest列出的244份旧失败/夹具错误/历史快照原字节逐hash一致。没有覆盖旧报告。
- 原80的五份JUnit重新只读解析，58backend+4正常UI+10独立backend/SQL+6独立UI+2独立R8=80唯一节点，80PASS/0FAIL/0ERROR/0SKIP；五份已存exit记录均0，与final-summary精确吻合。
- root的已存regression-r8-final.xml有249唯一节点，243PASS/0FAIL/0ERROR/6SKIP。原完整log达到100%，结论为243 passed, 6 skipped in 738.40s；没有通过日志截断推断未完成套件。6个skip全部有明确理由“Application-role subprocess regression requires explicit isolated PostgreSQL”（五个persistent app-run PG subprocess/control/CRUD，一个internal lifecycle application-role）。不称PG验收通过。
- root仓库r8-final-freeze.json与独审candidate-freeze.json的401映射、map指纹、implementation和pyproject精确相同，故此恢复后代码桥无差异。没有将root249与独审80相加成新的唯一测试覆盖数，场景重叠保持分列。

证据：live-source-bridge.json、snapshot-bridge.json、report-manifest-check.json、existing-80-and-root-freeze.json、root-regression-existing.json/root-regression-nodes.json。本追加manifest只封存这些新读取结果与报告，不触碰原80产物。

剩余边界仍为原LIMITED PASS：真实客户旧库升级、PG、Windows、原生浏览器、真实/付费模型、人工语义、完整P-A/P-B及远端CI均NOT RUN。此次没有CI、浏览器、旧取消精确竞态、网络/权限扩大、部署、提交或push操作。最终普通分支commit/push及推送后SHA由root完成；此读取桥本身不证明远端CI或产品全验收。未发现当前代码与已存80/root249证据的精确字节不对应。
