# Root原件读取中的解析错误

以下为工具可见stderr的转录，**不是原始重定向stderr文件**。读取已结束的JUnit时，root的临时脚本对所有testcase都使用`c.attrib['name']`，碰到900秒中断所留的无name占位元素，产生：

```
Traceback (most recent call last):
  File "<stdin>", line 5, in <module>
KeyError: 'name'
```

当时此前的681输入字节比较已通过，后续临时读取尚未执行。原XML逐字保留，具有4个named PASS和1个无name/time=0.001占位。之后纯原件核验只把有name且无failure/error/skipped的节点计作PASS，并单独报告中断/占位；没有修改原XML或重跑产品来修复这个解析错误。
