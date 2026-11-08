# 数据是怎么流起来的

四个脚本各管一段，中间用文件交接。搞清楚这条链，出问题的时候能直接定位到哪一段。

```
PDF/EPUB/DOCX…
   │  extract_text.py
   ▼
_work/raw/chNN.txt            按章切好的纯文本
   │  agent 逐章精读 + 生成（这一步没有脚本）
   ▼
chapters/*.md  concepts/*.md  glossary.md  quiz.md  flashcards.md
   │  同时写
   ▼
manifest.json                结构清单，唯一的装配输入
   │  build_companion.py
   ▼
<slug>学习伴侣.html          单文件，数据以 const DATA = {...} 内嵌
   │  build_handbook.py 从每个伴侣里把 DATA 抠出来
   ▼
index.html                   统一入口，所有书的数据重排后塞进一个文件
```

## 第一段：抽取

`extract_text.py` 只做机械工作：按格式找可用解析器，转成纯文本，用正则找疑似章节标题行，按章切片。它不认识书的内容，切分错了要人工调。

判断切分对不对，看输出里的章节数。一本 11 章的书切出 30 个标题，通常是正文里的小节标题也被当成章标题了。

扫描件和数学书是例外。文本层没有字，或者公式被编码成 `cid:`，任何解析器都救不了。这时候脚本会警告，接下来只能按页读图。

## 第二段：写作

这一段没脚本。agent 读 `_work/raw/chNN.txt`，按 `references/pedagogy.md` 和 `templates.md` 产出 Markdown。

质量取决于读得细不细。跳过精读直接套模板，出来的是结构完整但没信息量的东西，一眼能看出来。

## 第三段：装配

`manifest.json` 是这一段的核心。它把"有哪些章、哪些概念、哪些题"从 Markdown 里抽出来变成结构数据，组装脚本只看它，不猜 Markdown 结构。

所以写完 Markdown 必须回头核对 manifest：章节 `id` 和文件名对得上没有，测验的 `chapterId` 是不是有效，`answer` 类型对不对（单选是索引数字，多选是数组，填空是字符串）。

`build_companion.py` 做的事：

1. 读 manifest 和所有 Markdown
2. Markdown 转 HTML（自带一个够用的转换器，处理标题、列表、表格、代码块、引用、链接）
3. 把 Mermaid 代码块转成待渲染的 `div`，交给运行时的 mermaid 库
4. 组装导航树、搜索索引、测验页、卡片页、术语页
5. 把整份数据序列化进 `const DATA = {...}`，套进 HTML 模板

产物是单文件，没有任何外部 CSS/JS 依赖（除了 Mermaid 走 CDN）。所以能 `file://` 直接打开，也能原样丢到 Pages。

## 第四段：整合

`build_handbook.py` 不重新读 markdown，而是从每个伴侣 HTML 里把 `const DATA = {...};` 抠出来反序列化。这样避免了两套渲染逻辑，也保证总入口里的内容和单书版一模一样。

抠出来之后要改四处，不改就出错：

**内链加前缀。** 单书里链接是 `#/chapter/ch01`，合并后必须变成 `#/book/<key>/chapter/ch01`，否则点进去还在当前书。

**测验 id 加前缀。** 每本书都从 `q01` 编号，合并后 `document.querySelector('[data-qid="q01"]')` 全指到第一题。按章节改写成 `ch01-q01` 这种形式，`data-qid`、`input` 的 `name`、manifest 里的 id 三处同步。

**测验页重新聚合。** 各书的"全部测验"页是各自生成的，有的书干脆是空占位。总入口里按章把题拼成一页，顺序按书、再按章。

**Mermaid 清洗。** 标签里的 ` | ` 和半角括号会让解析失败。只改方括号、花括号、边标签内部，`root((...))`、`A(...)` 这类形状语法不能动。

## 单文件里怎么装下四本书

不是 iframe 套娃。四本书的数据合并成一个 `BOOKS` 对象，路由形如：

```
#/cross/doc1                       跨书总览
#/book/hello-algo/path             该书学习路径
#/book/hello-algo/chapter/ch01     章节
#/book/hello-algo/quiz/all         全部测验
#/book/hello-algo/cards            抽认卡
```

`pageIdOf()` 负责把路径转成数据里的 key，剥掉 `chapter/`、`concept/` 前缀。忘了剥，页面渲染出空字符串，不报错，很难查。

进度按 `book:page` 存 localStorage，切书互不干扰。搜索是运行时遍历所有书的 `rendered` 字段做子串匹配，不预先建索引——几千页的量级，够用。

## 为什么不做成多文件站点

多文件就得有构建工具、本地服务器或者 `pushState` 路由。这三样都会让人"下载下来打不开"。单文件的代价是首次加载要解析一个 1 MB 的 JSON，慢一两秒。我认为值得。

## 验证和打包

`verify_handbook.py` 用真浏览器打开 `index.html`，按路由逐页走，检查渲染长度、测验判分、卡片翻转、搜索命中、进度持久、控制台报错。

`package_delivery.py` 只做三件事：补 `.nojekyll`、按模式挑文件、压成 zip。它不校验内容，内容对不对是验证脚本的事。

两个脚本的分工要分清：验证失败说明产物有问题；打包失败一般是路径或权限问题。
