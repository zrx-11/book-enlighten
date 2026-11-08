# 从零跑通一次

这份文档走一遍最完整的小例子：一本 PDF，做到 `index.html`。所有命令都在仓库根目录执行。

## 0. 准备

```bash
python3 --version          # 3.9 以上
python3 scripts/extract_text.py --check
```

`--check` 会列出可用的解析器。缺 PDF 的话装一下：

```bash
pip install pymupdf pdfplumber
```

验证环节要 Playwright 和 Chromium。先看看系统里有没有现成的：

```bash
which chromium chromium-browser google-chrome 2>/dev/null
```

有就记下路径，后面 `--chromium` 直接用。没有的话 `pip install playwright && playwright install chromium`，装不上就跳过验证，手工点一遍。

## 1. 建目录

```bash
mkdir -p 我的专题/01-算法图解/_work/raw
```

每本书一个子目录，前缀用两位数，`build_handbook.py` 按名字排序。目录名会成为页面标签的一部分，起得直白一点，`01-算法图解` 比 `01` 好。

## 2. 抽文本

```bash
python3 scripts/extract_text.py 算法图解.pdf --out 我的专题/01-算法图解/_work/raw/
```

输出像这样：

```
算法图解.pdf  1,284,392 字符  疑似章节标题 11 处
→ 我的专题/01-算法图解/_work/raw/算法图解.txt
```

看到 `cid:` 或大片方框，说明是扫描件或者字体嵌得有问题，别往下走。用 Read 按页读图，人工把每章的公式和记号抄下来。这一步慢，但没有别的办法。

## 3. 拆结构、写内容

这一步没有脚本能代劳，是 agent 的主要工作量。

先建结构地图，写在 `_work/结构地图.md` 里：

```
书名：算法图解 | 作者：Aditya Bhargava | 章数：11
ch01 算法简介
ch02 选择排序
...
```

然后按 `references/templates.md` 逐章写。每章一个文件，命名 `chapters/chNN-标题.md`。写作要求看 `references/pedagogy.md`，核心就三条：不跳步、给类比并说明失效边界、术语首次出现就定义。

写完配套文件：`glossary.md`、`patterns.md`、`cheatsheet.md`、`quiz.md`、`flashcards.md`，以及根部的 `SKILL.md`（学习总纲）。

## 4. 写 manifest

这是组装的唯一输入，结构不清楚 HTML 就是空的。最小可用版本：

```json
{
  "slug": "grokking-algorithms",
  "title": "算法图解",
  "subtitle": "用图说话的数据结构与算法入门",
  "book": {"title": "算法图解", "author": "Aditya Bhargava", "source": ["算法图解.pdf"]},
  "audience": "零基础",
  "goal": "系统掌握基础算法与复杂度分析",
  "learningPath": [
    {"step": "01", "title": "建立复杂度直觉", "chapterIds": ["ch01"], "checkpoint": "通过 ch01 自测"}
  ],
  "chapters": [
    {"id": "ch01", "title": "第 1 章：算法简介", "file": "chapters/ch01-算法简介.md", "difficulty": 1}
  ],
  "concepts": [],
  "glossary": [],
  "quizzes": [],
  "flashcards": []
}
```

先写空数组跑一次，看到页面能开、章节列表出来，再往里填题和卡。一次填完再调，出错不好定位。

`slug` 只用小写字母、数字和连字符。它同时是路由 key 和 localStorage 的命名空间，改了它，之前的学习进度就读不到了。

## 5. 组装单书

```bash
python3 scripts/build_companion.py \
  --manifest 我的专题/01-算法图解/manifest.json \
  --out 我的专题/01-算法图解/grokking-algorithms学习伴侣.html
```

输出会报章节数、测验数、卡片数和文件大小。数字对不上就是 manifest 漏了。

浏览器打开看一眼：左侧导航能不能点、随便点一道题看判分和解析、抽认卡翻不翻。

## 6. 多书就先写总览

只有一本书可以跳过这步，脚本会自己合成一页总览。多书时手写三篇：

- `00-跨书总览/README.md`：推荐学习顺序。每本书为什么排在这个位置，要写依据，不能只写"由浅入深"。
- `00-跨书总览/跨书概念映射表.md`：拿真实 manifest 对照，同一个概念在各书哪一章。别凭记忆写，写完要核对。
- `00-跨书总览/综合检验建议.md`：需要同时用到两本书知识的任务。

## 7. 出总入口

```bash
python3 scripts/build_handbook.py --root 我的专题/
```

```
发现 1 本书：
  - grokking-algorithms  01-算法图解  (算法图解)
已生成 我的专题/index.html (210 KB, 1 本书, 1 篇总览)
已生成 我的专题/index.md
```

书多的时候加 `--order "02,01,03"` 控制顺序，`--label "02-算法图解=图解算法"` 改显示名。

## 8. 验证

```bash
python3 scripts/verify_handbook.py --index 我的专题/index.html \
  --chromium /usr/local/bin/chromium \
  --report 我的专题/_build/verify_report.json
```

一次跑几十项检查，每项一行 PASS/FAIL。有 FAIL 会打印实际值，比如 `hello-algo 首章渲染 | 0 字符`，说明路由或数据有问题。

失败的项先分辨是产品问题还是断言问题。断言写死了初始状态（比如"应该是 2/17"），前面测试已经访问过章节，就会显示 3/17，功能没坏。改断言，别改产品。

## 9. 打包

```bash
python3 scripts/package_delivery.py --root 我的专题/ --out 我的专题.zip --mode final
```

```
已创建 .nojekyll
已生成 交付说明.md
打包完成：我的专题.zip
  模式：final | 文件：169 | 大小：1.1 MB | 排除：约 136 个中间文件
  完整性：OK
```

`--mode full` 会把 `_work/`、`_build/` 一起打进去。要不要带，取决于你想不想公开中间过程。

最后解压到 `/tmp` 之类的地方，双击 `index.html` 再确认一次。压缩包里的路径和原目录不一样，相对链接出错只有在这里才暴露。
