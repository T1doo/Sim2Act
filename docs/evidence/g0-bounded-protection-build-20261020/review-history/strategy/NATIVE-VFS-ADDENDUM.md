# 补充：根提出原生VFS代理候选后

根已选择进一步实施原生代理；前份STRATEGY-REVIEW对stdlib/Python文件白名单不足的结论，不是“原生VFS必定不可行”的判断，也不是阻止本轮授权的构建/纯单元工作。该候选尚未提交具体代码，以下仅为实现审查清单，不是启动ACK。

[SQLite VFS接口](https://www.sqlite.org/c3ref/vfs.html) 和 [io_methods](https://www.sqlite.org/c3ref/io_methods.html) 是本候选的主要依据：版本决定可访问的字段，xOpen失败仍须正确处理pMethods。应验证同一已加载_sqlite3动态库的符号与ABI，不链接或加载另一份SQLite；C对象和callback寿命覆盖全部连接，底层文件布局按实际szOsFile及正确对齐分配。未知版本/空方法必须拒绝，不能靠未声明布局运行。

xOpen限定新绝对fixture.db及三个后缀，同时核实flags对应角色；NULL随机temp、其他库/路径全部拒绝。xFullPathname、xAccess、xDelete亦需精确限制，检查root/文件普通性、链接和现有大小。文件名数并不等于活inode数：如果仍有fd时unlink再重建同名文件，旧inode仍占空间。必须跟踪slot/open-handle/inode或禁止相应生命周期，不能只事后数4名字。默认VFS还可经URI指定旧VFS绕过；固定URL、connect/ATTACH闭合和入口拒绝须实核，原生恶意调用不在有限可信产品闭包保证之内。

xWrite/xTruncate要对非负offset/amount及加法溢出执行前检查。xShmMap委托会在底层自行打开-shm，须核其实际后缀、region乘加边界及增长；不能声称它都经过上层xOpen。xFetch映射可直接暴露字节，最小保守实现可返回NULL回落xRead，但须说明性能扰动；不可让映射写绕过界限。xUnfetch须与该策略一致。

[官方file-control列表](https://www.sqlite.org/c3ref/c_fcntl_begin_atomic_write.html) 说明SIZE_HINT可预分配、CHUNK_SIZE影响扩容、MMAP_SIZE涉及映射、部分opcode可提供文件/VFS指针。因而xFileControl应默认NOTFOUND/拒绝，对真正必需项逐一证明无未受控副作用或先检界限；不能盲委托PRAGMA、SIZE_HINT、CHUNK_SIZE、MMAP_SIZE、TEMPFILENAME、atomic及扩展自定义项。FILE_POINTER/JOURNAL_POINTER/VFS_POINTER由核心/底层处理细节需明确，至少不能泄露底层未保护file对象。锁/同步/原atomic设备特性必须保留或按官方合同保守解释，不得通过伪造同步、no-op写或改journal/temp_store使单元“成功”。

文件64MiB证明要同时涵盖全部活DB inode、底层SHM和Python有界writer、父stdout/receipt；编译器和纯单元自己的/tmp产物与未来运行目录分开记账。纯SQLite单元可测试准确cap、越界写/截断/SHM、randomtemp/URI/附库拒绝、链接/已有超大文件、unlink-open重建及filecontrol异常路径，但不能据此直接宣布真实六Mock前缀已验证。任何无法闭合项仍使入口BLOCKED。

仅只读源码与官方资料；本人未编译/导入该候选、未运行SQLite/测试/产品/fixture/Worker/Mock/PB/G0或launcher。根独占所有仓库修改和授权内纯单元执行。
