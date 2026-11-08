# 点化 · Book Enlighten

把一本书，或者同一主题的一堆书，拆成一套能直接开学的知识库。最后收进一个 `index.html`，双击就能学。

我读专业书一直有个毛病：读的时候都懂，合上书就散了。后来改成先拆目录、再画概念依赖、最后按依赖顺序学，效果确实好，但每本书都要重来一遍，很费时间。这个仓库就是把我自己那套手工流程固定下来，交给 agent 去跑。跑完拿到的不是读书笔记，是一套能按图索骥学下去的东西。

产物有四个部分：

- `index.html`：总入口。单文件，离线可开，所有书在这里切换
- 每本书一个独立的学习伴侣 HTML，可以单独发给别人
- 一套 Markdown 知识库，Obsidian 或 VS Code 直接打开
- 一个 zip，按需带上或去掉中间过程文件

---

## 一、它跟"写个摘要"有什么不一样

摘要解决的是"这本书讲了什么"。点化解决的是"一个零基础的人怎么把它学会"。

具体差别在四件事：

**拆的是结构，不是段落。** 先把全书拆成部、章、节，再从正文里抽出概念和它们的前后依赖。学的时候按依赖的拓扑序走，而不是按书的页码走。有些书第三章要用第五章的概念，硬着头皮读下去只会卡住。

**抽的是作者的心智模型。** 作者反复用的分析框架、判断规则、明确反对的做法，单独整理成模式库。这部分书里往往散在各章，不集中读一遍看不出来。

**写的是零基础能读的讲解。** 每个抽象概念配类比、图示、实例三样里至少两样，讲清楚类比在哪儿失效，把最容易错的理解单独列出来纠正。术语第一次出现就给白话定义。

**配的是能测的记忆系统。** 每章有自测题，答案带解析，另配抽认卡和复习锚点。学没学会靠做题验证，不靠"感觉看懂了"。

---

## 二、一套产物长什么样

拿四本算法书举例（Hello 算法、算法图解、算法（第 4 版）、算法导论），跑完是这么个目录：

```
算法专项-点化学习系统/
├── index.html                    1.1 MB，总学习手册，双击就开
├── index.md                      Markdown 导航，给不想开浏览器的时候用
├── README.md                     部署说明
├── .nojekyll                     GitHub Pages 用
├── 交付说明.md                    书目统计、目录用途、验证结论
├── 00-跨书总览/
│   ├── README.md                 推荐学习顺序，每步给依据
│   ├── 跨书概念映射表.md          同一个概念在四本书里各在哪一章
│   └── 综合检验建议.md            跨书整合题
├── 01-hello算法/
│   ├── SKILL.md                  该书学习总纲
│   ├── chapters/                 17 章精讲
│   ├── concepts/                 跨章概念页
│   ├── glossary.md  patterns.md  cheatsheet.md
│   ├── quiz.md  flashcards.md
│   ├── manifest.json             结构化清单，组装 HTML 靠它
│   └── hello-algo学习伴侣.html    单书版
├── 02-算法图解/ …                 11 章，37 道题
├── 03-算法第四版/ …               25 节，22 道题
├── 04-算法导论/ …                 39 单元，43 道题
└── _build/  _work/               中间产物（full 模式才带）
```

`index.html` 里能做的事：

- 顶部切换四本书和「跨书总览」
- 左侧按书看学习路径、章节、概念、测验、抽认卡、术语表、模式库、速查表
- 搜索框一次搜全部书，结果标出是哪本书哪一章
- 每本书的进度分开记，刷新、关浏览器都不丢
- 测验选完立刻判对错，附解析
- 抽认卡点一下翻面，认识的记一笔
- 深色模式，晚上看眼睛舒服点

四本书加起来 92 章（含节/单元）、135 道题、252 张卡。这个体积全在一个 HTML 里，靠的是把各书 HTML 里内嵌的数据抽出来重新拼装，不是把四个文件塞进 iframe。

---

## 三、安装

这个仓库本身就是 skill 目录，clone 到 agent 的 skills 目录即可。

```bash
# 豆包 / 通用 agent 的用户级技能目录
git clone https://github.com/<你的用户名>/book-enlighten.git \
  ~/.doubao/agent_mode/workspace/.user_skills/book-enlighten
```

目录名要和 `SKILL.md` 里的 `name: book-enlighten` 对得上，不然有的加载器会报名字不一致。用其他 agent（Claude Code、Codex 之类）时，放进它自己的 skills 路径，结构一样。

不需要安装什么框架。硬性依赖只有 Python 3.9 以上和标准库。

按格式补解析器，缺哪个装哪个：

```bash
pip install pymupdf pdfplumber python-docx ebooklib
# PDF 也可以走系统自带的 pdftotext
sudo apt install poppler-utils
```

跑端到端验证的话，还要 Playwright 和一个 Chromium：

```bash
pip install playwright
# 系统里有 chromium 就直接用，不用额外下载
python3 scripts/verify_handbook.py --index index.html --chromium /usr/local/bin/chromium
```

Playwright 自带的浏览器包在有些机器上装不全，`playwright install` 也可能拉不下来。这种时候别折腾，`--chromium` 指到系统已有的 Chromium 就行，加 `--no-sandbox` 是脚本内部已经处理好的。

---

## 四、跑一次

假设你有一本 `算法图解.pdf`，想做成学习系统。

**1. 先看解析器情况**

```bash
python3 scripts/extract_text.py --check
```

**2. 抽文本、切章节**

```bash
python3 scripts/extract_text.py 算法图解.pdf --out 算法专项/02-算法图解/_work/raw/
```

输出会告诉你总字符数和疑似章节标题的行。数学类 PDF 如果抽出来全是 `cid:` 或者方框，别用了，直接按页读图——脚本会给警告，但看不出公式这件事它救不了。

**3. 写知识库**

这一步是 agent 干的活，也是整个流程里最花时间的部分：按 `references/templates.md` 逐章写精讲、概念页、术语表、测验、抽认卡，最后写一个 `manifest.json` 把结构登记清楚。教学法的要求写在 `references/pedagogy.md` 里，工作流在 `references/workflow.md`。

**4. 组装单书伴侣**

```bash
python3 scripts/build_companion.py \
  --manifest 算法专项/02-算法图解/manifest.json \
  --out 算法专项/02-算法图解/grokking-algorithms学习伴侣.html
```

**5. 整合总入口**

多本书时，先写 `00-跨书总览/`，再跑：

```bash
python3 scripts/build_handbook.py --root 算法专项/
```

单本书也能跑，脚本会自动合成一页总览。产出 `index.html` 和 `index.md`。

**6. 验证**

```bash
python3 scripts/verify_handbook.py --index 算法专项/index.html
```

真实浏览器跑，逐书检查首末章渲染、每本书的测验能不能答对、抽认卡翻不翻、搜索有没有结果、进度刷新后还在不在、控制台有没有报错。有失败项会列出来，退出码非 0。

**7. 打包**

```bash
# 只要最终产物
python3 scripts/package_delivery.py --root 算法专项/ --out 算法专项.zip --mode final
# 连中间产物一起
python3 scripts/package_delivery.py --root 算法专项/ --out 算法专项-full.zip --mode full
```

`final` 排除 `_work/`、`_build/`，四本书的情况下是 169 个文件、1.1 MB。`full` 全带，305 个文件、12.7 MB。

---

## 五、命令速查

| 命令 | 用途 | 常用参数 |
|---|---|---|
| `extract_text.py --check` | 看有哪些解析器可用 | — |
| `extract_text.py <文件…> --out <目录>` | 抽文本并按章切分 | `--out` |
| `build_companion.py --manifest … --out …` | 单书 HTML | `--manifest` `--out` |
| `build_handbook.py --root …` | 总入口 HTML + index.md | `--out` `--order "01,02"` `--label` `--cross-dir` `--no-md` |
| `verify_handbook.py --index …` | 浏览器端到端验证 | `--chromium` `--report` |
| `package_delivery.py --root … --out …` | 打包 | `--mode final\|full` |

`build_handbook.py` 的发现规则很朴素：根目录下每个含 `manifest.json` 又有 `*.html` 的子目录算一本书。书的路由 key 取 `manifest.slug`，没有就按目录序号生成 `b01`。跨书总览目录默认找 `00-*` 或名字里带"总览"的，里面所有 `.md` 都会渲染成页面，标题取第一个 `#`。

顺序想自己定，用 `--order "02,01,03"`；标签想改，用 `--label "02-算法图解=图解算法"`。

---

## 六、manifest 是什么

`manifest.json` 是知识库和 HTML 之间的合同。章节、概念、术语、测验、卡片全部登记在里面，`build_companion.py` 和 `build_handbook.py` 都只认这个文件，不去猜 Markdown 的结构。

一个最小片段：

```json
{
  "slug": "grokking-algorithms",
  "title": "算法图解",
  "chapters": [
    {"id": "ch01", "title": "第 1 章：算法简介", "file": "chapters/ch01-算法简介.md", "difficulty": 1}
  ],
  "quizzes": [
    {"id": "q01", "chapterId": "ch01", "type": "single",
     "question": "二分查找的时间复杂度是？",
     "options": ["O(n)", "O(log n)", "O(n²)"], "answer": 1,
     "explain": "每次把候选区间砍半，最多 log₂n 步。"}
  ],
  "flashcards": [
    {"id": "f01", "chapterId": "ch01", "front": "二分查找的前提是什么？",
     "back": "数据有序。", "tags": ["查找"]}
  ]
}
```

几条硬规矩：`chapterIds` 必须能对上 `chapters[].id`；`answer` 的类型要跟 `type` 一致（单选是索引，多选是索引数组，填空是字符串）；`explain` 不能空。完整 schema 见 `references/templates.md` 第 10 节。

---

## 七、几个设计上的取舍

**为什么是单文件 HTML。** 不依赖本地服务器，不用 `npm install`，发给别人就一个文件，扔到 Pages 上也不用改配置。代价是体积大，四本书 1.1 MB，浏览器打开要等一两秒。我认为这个交换划算。

**为什么用 hash 路由。** `file://` 下 `history.pushState` 会被拦，而很多人就是双击打开。`#/book/grokking-algorithms/chapter/ch01` 这种路径在本地和 Pages 上行为一致，也省掉了配 rewrite 规则。

**为什么不做摘要，也不做 RAG。** 这两件事目标不同。RAG 是"我要找书里某句话"，点化是"我要从零学会这本书"。混在一起会把学习内容写成检索片段，读起来断断续续。真需要检索，全文搜索框就够了。

**为什么交付分两种模式。** 公开仓库放 12.7 MB 的中间产物不合适，但中间产物对复查、二次加工有用——抽取的原文、扫描页截图、构建脚本、验证报告都在里面。所以做成开关，用户自己选。两种都附一份 `交付说明.md`，写清目录用途和验证结论。

**为什么验证要开真浏览器。** 静态检查查不出路由写错、选择器失效、localStorage 不持久这些事。我早期吃过亏：断言写死了"2/17"，结果前面测试已经访问过章节，页面显示 3/17，看起来像功能坏了，其实是我的测试有问题。所以现在断言尽量写成"刷新前后一致"这种不依赖初始状态的判断。

---

## 八、部署到 GitHub Pages

站点就是几个静态文件，不需要 Actions。

```bash
# 1. 把交付包里的文件全部放到仓库根目录（注意是根目录，不是子文件夹）
cd <仓库目录>
git add -A
git commit -m "点化学习系统：总手册与各书伴侣"
git push origin main

# 2. 仓库 Settings → Pages → Source 选 Deploy from a branch
#    Branch: main，目录选 / (root)，保存

# 3. 等一两分钟
#    https://<用户名>.github.io/<仓库名>/
```

新仓库第一次推送的话：

```bash
git init
git add -A
git commit -m "点化学习系统"
git branch -M main
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

`.nojekyll` 这个空文件别删。GitHub Pages 默认走 Jekyll，它会忽略所有以下划线开头的目录，`_build/`、`_work/` 直接 404；中文文件名偶尔也会被处理坏。放个 `.nojekyll` 就是告诉它"别管，原样发出去"。打包脚本会自动补这个文件。

常见故障：打开 404 先检查 `index.html` 是否真在根目录、Pages 分支和目录选对没有；刚开启要等一会儿。中文文件名 404 的话，`index.html` 内部用的是 hash 路由不受影响，单书伴侣的外部链接脚本里已经做了 `encodeURI`。Mermaid 图不显示是 CDN 没连上，离线时图会降级成源码，这是有意为之。

---

## 九、踩过的坑

都是实际跑出来的，写在这儿省得下次再撞。

**各书的测验 id 会撞。** 每本书都从 `q01` 开始编号，合并到一个页面后 `document.querySelector` 全指到第一题。解决办法是按章节给 id 加前缀，`data-qid`、`input` 的 `name`、manifest 里的 id 三处一起改。`build_handbook.py` 里做了这件事，自己改脚本时别漏。

**各书的"全部测验"页可能是空占位。** Hello 算法那本的 `__quiz_all__` 只有一行"（无综合题）"，直接搬过来就是空白页。得按章把题目拼起来重新渲染。

**路由解析要剥前缀。** `pageIdOf` 如果不把 `chapter/`、`concept/` 剥掉，页面会渲染出一片空白，而且不报错，很难查。

**Mermaid 对标签里的符号很挑。** 节点文字里有 ` | `、有半角括号（`O(n)`、`det(A)`），解析就失败，整张图变成错误提示。但 `root((数据结构))`、`A(圆角)` 本身是合法形状语法，不能无脑全局替换。现在的做法是只改方括号、花括号和边标签内部的括号，改成全角。这样两头的形状语法不受影响。

**Playwright 的浏览器包可能缺失。** 报找不到 `chromium_headless_shell` 的时候，用系统 Chromium 救急：`--chromium /usr/local/bin/chromium`，启动参数带 `--no-sandbox --disable-gpu`。

**验证脚本自己也会骗人。** 断言写得太死、选择器写错，都会制造"功能失效"的假象。遇到失败先在一个干净的浏览器状态里手动点一遍，确认是产品的问题还是测试的问题，再决定改哪边。

---

## 十、它做不到的事

- **扫描版 PDF 里的公式它读不出来。** 文本层是图片，抽出来是乱码，得按页读图。公式多的书，人工核对量不小。
- **写得对不对，取决于书读得够不够细。** 脚本只保证结构和交互，内容质量靠逐章精读。想省这一步，出来的就是漂亮但空的东西。
- **Mermaid 语法是薄弱环节。** 作者原文里的图如果写法古怪，清洗规则不一定兜得住，偶尔会降级成源码。
- **页面上限。** Pages 单仓库 1 GB、单文件 100 MB。四本书带中间产物 12.7 MB 没压力，但塞十几本大部头、还全是扫描页截图，就会顶到边。
- **多书的概念合并是启发式的。** 同义不同名（"散列表"和"哈希表"）能靠人工写进映射表，脚本自己判断不了。

---

## 十一、仓库里都有什么

```
book-enlighten/
├── SKILL.md                 技能入口，agent 读这个
├── README.md                本文件
├── LICENSE                  MIT
├── agents/doubao.yaml       面板显示名（中文）
├── references/
│   ├── workflow.md          九个阶段的操作细节与命令
│   ├── pedagogy.md          零基础教学法
│   ├── templates.md         全部产物模板 + manifest schema
│   ├── open-source-patterns.md  参考过的开源项目与差异
│   └── github-pages.md      部署步骤与故障排查
├── scripts/
│   ├── extract_text.py      多格式文本抽取
│   ├── build_companion.py   单书 HTML 组装
│   ├── build_handbook.py    总入口组装（单书/多书通用）
│   ├── verify_handbook.py   浏览器端到端验证
│   └── package_delivery.py  final / full 打包
└── docs/
    ├── quickstart.md        从零跑通一次的完整例子
    ├── pipeline.md          数据怎么从 PDF 流到 index.html
    └── troubleshooting.md   按症状查的排错表
```

`SKILL.md` 控制在 80 行以内，细节都摊在 `references/` 里，agent 需要时再读，不占上下文。

---

## 十二、参考过的项目

设计不是凭空来的，下面几个开源项目给了我很多具体做法：

- [book-to-skill](https://github.com/virgiliojr94/book-to-skill)：确定性抽取器 + 规格驱动生成，manifest 按需加载
- [book-to-visual-companion](https://github.com/sanjaygupta-professional/AINativeAgileLearning)：Mermaid 概念图与学习路径的可视化站点
- book-reader：阅读器式导航与进度
- Book-to-Course：模块 + 检查点的课程化拆解
- repo-mastery：学、测、复习的循环
- cangjie-skill：技能工程化的目录规范

和它们的差别主要在两点：一是把多本书收进一个统一入口，二是交付粒度可选、并且默认就能挂 Pages。这两件事上面几个项目基本没做。

Mermaid 渲染用 [mermaid](https://mermaid.js.org/)，MIT 许可。

---

## License

MIT，见 [LICENSE](LICENSE)。
