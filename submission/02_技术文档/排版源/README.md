# 产品书排版源

正文数据为上一级的 `产品书内容结构_v01.json`。修改后运行本目录 `render_product_book.py`，会重新生成同名PDF、Markdown及待复核的检查记录。需Python、reportlab、pypdf，以及Windows微软雅黑字体；图片沿用项目 `submission` 中的原路径。

重新生成后用Poppler渲染16页并重新目视检查，不沿用旧的通过记录。文件不依赖C盘下载目录或 `.local` 中的临时制作脚本。
