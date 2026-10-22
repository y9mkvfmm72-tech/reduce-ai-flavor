---
name: reduce-ai-flavor
description: 把 AI 参与过的学生文档改到"看不出是 AI 做的"。覆盖实验记录本、实验报告、实习报告、课程论文、读书报告、文献综述、开题报告、毕业论文、实验问答题、汇报与答辩讲稿——凡是署名交给老师、助教或答辩委员会的东西。含七层泄漏诊断（词汇 / 论证 / 节奏 / 叙事 / 文件 / 闭合 / 修辞）、文类路由（哪几层对该文类算证据）、中英文字反模式、模式 A/B/C、docx run 级改写、补图与逐格验收，以及三个可量化脚本：flavor_audit.py（像不像模型写的，`--genre` 选文类）、consistency.py（说的和表对不对得上）、overlap.py（像不像抄参考稿）。
whenToUse: 用户说"降 AI 味/去 AI 感/别像 AI 写的/AI 味重吗/这个答案 AI 味重吗/这段像不像 AI/查重/和参考稿太像/交上去看不出是 AI"，或问实验记录本、实验报告、实习报告、课程论文、读书报告、文献综述、开题报告、毕业论文、实验问答题、答辩讲稿、小组作业里任何一份"读起来不像我写的"。
metadata:
  verified: 2026-10-21
  source_cases:
    - 黑体辐射 lab book：AI 写分析段 → 去论证味（v2→v3）
    - 同一份 lab book 的 v1→v2：三处断言与自己的表不符（nearly the same / integrating gives the total / K(λ) of Table 1）
    - 同题 lab book：版式改写（原稿 8 页 → 定稿 5 页）
    - 同一份 lab book 的 v3→v4：正文 4 处描述曲线而文件 0 张图；机制句 2 处与表矛盾；1 处 x%→4x% 占位符
    - 密立根油滴七道短答题（2–4 分/题，每题 2–4 段）：第 1 层 0 命中、第 3 层 sd/mean 0.39–0.52、第 2 层 defence 0，但第 7 层抽样 2 / 6 / 7 个信号
  measured:
    - 套话 0/38、sd/mean 0.52 仍像 AI；defence 4→0、meta 1→0、clock 0→2 后通过
    - 断言与表矛盾 3 处 → 0；符号残留（σ/δ）1 处 → 0；交叉引用错 1 处 → 0
    - 正文散文与参考稿重合 3.2% → 0.6%
    - v4：图 0→1、正文曲线词 16→1；机制句 2→1；占位符 1→0；图与表口径差 2%（800 nm）已在图注声明
    - 短答题两组配对实测：q1 句数 7→5、第 7 层 2→1；q7 句数 8→9、第 7 层 6→2（拆句降信号，但不降句数）
---

# 降低 AI 味道

## 适用范围

判据只有一条：**这份东西要署你的名字交给老师 / 助教 / 答辩委员会，而他们有理由怀疑不是你写的。**

不限于实验报告。学生文档是一个谱系，从"几乎全是记录"到"几乎全是论述"，该看哪一层差别很大：

| 文类 | `--genre` | 先看 | 不适用 | 这一文类的头号问题 |
|---|---|---|---|---|
| 实验记录本 | `notebook` | 4 → 6 → 2 | — | 没有时间 / 等待 / 重测，读起来像成品报告 |
| 实验报告、实习报告 | `report` | 6 → 2 → 4 | — | 描述看不见的图；断言与自己的表不符 |
| 实验问答题、短答题 | `answer` | 7 + 篇幅 | 4, 6 | 答得比题目要求多 2–3 倍（§4.5） |
| 课程论文、读书报告、文献综述 | `paper` | 2 → 7 → overlap | 4 | 三段式；与参考文献重合 |
| 开题报告、毕业论文 | `thesis` | 2 → 6 → 7 | 4 | 机制句指不到自己的表；论证靠修辞撑 |
| 汇报讲稿、答辩稿 | `talk` | 7 | 4, 6 | 排比、金句、每节一句升华 |

`--genre` 不是标签，是**决定哪几层算证据**。选错文类会把好文档判成坏的：一份课程论文没有时间戳是正常的，一份实验记录本没有时间戳就是破绽。

**不适用**：整份内容都不是作者的（那是代写）；纯数据文件；代码。

## 0 先判场景：AI 碰过哪一层

同一份文档，修法可以完全相反。先做一件事：拿当前稿和**上一版 / 作者原稿**逐段 diff。

| 场景 | 判据 | 修法 |
|---|---|---|
| A 只碰过版式、翻译 | 句子能逐字对回原稿，只是位置、样式、译法变了 | 文字回到原稿，只动版式（§2A） |
| B 写过正文（分析段、讨论段、结论） | diff 出整段新文字，原稿里没有 | 允许删 / 压 / 降调，不许新增事实（§2B） |
| C 短答题、实验问答题 | 只有 2–4 段，没有表格、时间戳、图；题目本身就在眼前 | 先按分值砍长度，再只改句法（§2C、§4.5） |

场景 C 没有原稿可 diff，判据换成**句数 ÷ 分值**；第 4 层（叙事）和第 6 层（物件）在这一文类里不适用，`--genre answer` 会把它们标成 n/a，别把 n/a 当证据。

只有 diff 出来的段落才是嫌疑段。作者自己写的段落，一个字都不要顺手"润色"——润色本身就是 AI 味。

模式 B 的前提：**数据、实验、结论都是作者自己的**，只是措辞由机器起草。如果整份文档连内容都不是作者的，本技能不适用，那是代写。

**开工前两个 5 秒检查**（省掉后面的争论）：

1. **来源**：`grep -rF "整句特征原文" 工作区/`。如果这句话硬编码在 `build_*.py` 的字符串里、只出现在 git 历史里，或者上一版里根本没有，那"是不是 AI 写的"已经有答案——剩下的问题只是"看不看得出"，不是"是不是"。
2. **物件**：`len(Document(p).inline_shapes)` 和 `len(Document(p).tables)`。正文在讲图 / 表而文件里没有，比任何句式都硬（§1 第 6 层、§4 补图）。

先跑 `flavor_audit.py` 看七层里哪层亮红（短答题加 `--genre answer --marks N`）；文档有表时再跑 `consistency.py` 看断言和表对不对得上。最常见的误判是"以为要改词，其实要删论证"；第二常见的是"以为要改句，其实要补图"；第三常见的是"以为要改词，其实要砍长度"。

## 1 七层泄漏（flavor_audit 数 1–7 层，consistency 查第 6 层的表格侧）

| 层 | 泄漏物 | 判据 | 可靠性 |
|---|---|---|---|
| 1 词汇 | delve / moreover / 综上所述 | 套话表 | 低 |
| 2 论证 | 预先辩护、元话语、统一三段式、即时量化、机制填充、占位符 | 句子在保护结论，不是在报告结果 | 高 |
| 3 节奏 | 句长过于均匀 | sd/mean < 0.35 | 低 |
| 4 叙事 | 零过程：没有等待、重测、漂移、异常 | 记录文类里 0 个时间戳 / 时长 | 高（短答题不适用） |
| 5 文件 | U+2060、字体混用、缩略图、缺字回退 | 脚本扫、逐页看图 | 高（机械） |
| 6 闭合 | 断言与自己的表 / 符号 / 交叉引用对不上；图与表缺失 | "几乎不变 / 等于总量 / 见 Table N"经不起复算；正文描述曲线而文件 0 张图 | 高（最硬） |
| 7 修辞 | 成对破折号、倒装、隐喻、对偶、三段式标记、预告式列举、括号补充、镜像段落、收束句 | 句子在替自己修辞，不是在答题 | 高（短答题主判据） |

**第 7 层是为"没有表、没有图、没有时间戳"的文本准备的。** 七道短答题实测：第 1 层 0 命中、第 3 层 sd/mean 0.39–0.52、第 2 层 defence 0 / meta 0–1——前六层几乎全 PASS，但抽样三题的第 7 层信号仍有 2 / 6 / 7 个。这一层的信号不靠词表，靠**结构**：一句话里两个破折号、`Only under X are Y valid` 这种倒装、`is the bridge between A and B` 这种隐喻、两段用同一个句子骨架、每段末句都在替结论收口。

第 7 层与第 2 层的分工：第 2 层问"这句话是不是在保护结论"，第 7 层问"这句话是不是为了好听才这么写"。前者删掉就没了，后者**删不掉，只能改写**——这是两套不同的修法，别混。

语域断层（操作段是手册翻译腔、分析段是流利英文）不在脚本里，要自己读；见 §4 最后一行。

**第 6 层不是文风问题，是事实问题。** 一句 `nearly the same` 对着 6.2% 的散布、一句 `integrating … gives the total exitance` 对着只有 70% 覆盖的窗口、一句 `K(λ) of Table 1` 而 Table 1 里只有 I–T——老师拿计算器三分钟就能发现。它比任何句式都更能说明"写句子的人没在看数据"，而且删形容词修不好：句子本身是错的。

**第 6 层还有另一半：物件存在性。** 同一案的下一轮（v3→v4）里，`flavor_audit` 的 [2]/[4] 只亮了两项，但正文有 4 处描述曲线形状、引用 `the Planck curves`，而 `.docx` 的 `inline_shapes = 0`、导出 PDF 的 `/Image = 0`。读者根本看不到你描述的曲线——**补一张实测 vs 理论的图，比改十句措辞有效**，而且它顺手把讨论段从"复述教科书"逼回"报告这张图"。本案例补图后：images 0→1、正文曲线词 16→1、[6] 由 STRIP 转 PASS。

**第 5 层现在自动数两样东西：字体家族和加粗引导词。** `flavor_audit.py` 会多打两行 —— `fonts: 仿宋_GB2312 56, Segoe UI 12  2 Latin families …` 和 `bold lead-ins: 7`。字体家族 ≥3 基本可以断定是拼接：一次坐下来敲完的文档只有一到两种西文字体。加粗引导词是 markdown 转 docx 的残留 —— 七步操作全是 `**1. Adjustment of the apparatus.** Level the main unit…` 这种「短加粗标签 + 普通句」的形状，手打的人不会给每一步都加粗前三个词，更不会七步一样长。修法只有一个：**去掉加粗，文字一个不动**（本案例 8 处 bold → 0，句子一个字没改，第 7 层信号从 11 个分号降到 0）。

**实测反例（本技能来源案例）**：38 条英文套话 **0 命中**；句长均值 24.6 词、标准差 12.7、sd/mean **0.52**（比多数人写得还"像人"）。但文档仍然一眼 AI：6 条讨论全是"断言 → 数字 → 预先辩护 → 结论"同一个模子，4 处辩护句、1 处元话语、正文 0 个时间戳。

结论：**套话表和句长方差都不足以判定。** 它们只能当辅助指标。

**数据自洽不算 AI 味。** 同一次实验、同一台仪器扫出来的数，两边本来就该一样；数字相同是证据，不是缺陷。把它和文字重合分开统计。

## 2 铁律

### 模式 A：AI 只碰过版式 / 翻译
1. **文本只有一个来源：作者原稿。** 用 `python-docx` 程序化取出段落原文，不要手打。
2. **只动版式，不动句式。** 允许改字体、字号、行距、边距、对齐、表格结构、上下标、破折号、页码、表题位置、分页；不允许改动词、语序、连接词、we/I 的使用、术语的口语说法。
3. **参考稿只看版式，不看文字。** 眼睛停在"表题在上还是在下""表头有没有底色""数字怎么对齐"；短句会自己爬进来——见 §7 末尾。
4. **不编数据。** 空格子只有三条出路：查仪器原始文件、问用户、改表结构删掉这一项。

### 模式 B：AI 写过正文
5. **只删不增。** 删辩护、删元话语、删 verdict；**数字和事实一个不动**。改写不是重写，是减脂。
6. **过程细节只从记录里来。** 仪器文件头的保存时间、表格里的采集设置、实验记录本、重测备注。没有记录就不写。
7. **改完给作者 diff。** 标出改了哪几句，让本人确认——这是"改写"和"代写"的分界。
8. **缺原因就写"无记录"并标出来**，不要编一个看起来合理的原因（例：两条谱线为什么没参与分析）。
9. **删不掉的错句要重写，重写后的每个断言必须能从原表复算。** 只删形容词会留下一个语法通顺、数据没根据的句子——那是另一种 AI 味。改完的每一句，问一次"它引的那个数，在表里算得出来吗"。

### 模式 C：短答题，只动句法

10. **数字、公式、结论一个不动。** 用户说"这个不需要修改""内容一个字不动"时走这条；能改的只有句法、句序、句长、连接词。物理 / 内容层面的问题单独列出来问，不要顺手改掉——用户可能就是要保留那个说法。
11. **先砍长度，再改句子。** 句数 ÷ 分值 > 2 时，砍内容比改句法有效十倍。只换同义词，第 7 层的信号一个都不会少。
12. **改写后重跑 `--genre answer --marks N`。** 第 7 层要降到 ≤2 个信号、没有镜像段落。降不下来说明只换了词，句法没动；句数没降说明只拆了句，内容没删。两个指标各自独立，见 §4.5 校准。

## 3 诊断：先量化，再动笔

```bash
python scripts/flavor_audit.py 记录本.docx                    # notebook（默认）
python scripts/flavor_audit.py 实验报告.docx --genre report
python scripts/flavor_audit.py 课程论文.docx --genre paper     # 或 thesis / talk
python scripts/flavor_audit.py 定稿.docx --tables             # 表格也算进语料
python scripts/flavor_audit.py 答案.txt --genre answer --marks 4   # 短答题
python scripts/consistency.py 定稿.docx                       # 有表时必跑
```

输出七层，逐层 `PASS / REVIEW / STRIP`，并把**具体句子**列出来。真正要看的是四层：

- `[2] argument`：defence / meta / mechanism 各几句、是哪几句。这几句就是待删清单；`x%` 这类占位符也在这一层（placeholder）。
- `[4] narrative`：clock / duration 是否为 0。是的话补真实过程记录。短答题这一层标 `n/a`，不是问题。
- `[6] artefacts`：images 是不是 0、有没有 `Figure N` / `Table N` 引用却没有对应物件。这一层 STRIP，说明有人在描述看不见的东西，先补图再改句。
- `[7] rhetoric`：em-dash pairs / inversion / metaphor / antithesis / essay markers / asides / closure / mirrored paragraphs。每个非零项都把那句原文打出来。**短答题先看这一层，再看 `--marks` 给的句数预算。**

`consistency.py` 不是文风工具，是核对工具：它把"近常数"的表行连同散布列出来、把文中找不到出处的数、只用一两次的希腊符号、`of Table N` 的交叉引用、以及正文引用的图/表在文件里是否存在，逐条摊开，让人拿计算器对。输出分六组，用法见 §10。

校准（本案例，v2 → v3）：

| 指标 | v2（待改） | v3（改后） | 说明 |
|---|---|---|---|
| 套话命中 | 0 | 0 | 不说明问题 |
| sd/mean | 0.52 | 0.49 | 不说明问题 |
| defence / meta | 4 / 1 | 0 / 0 | **问题在这里** |
| clock / duration | 0 / 0 | 2 / 0 | **第二个问题** |
| U+2060 | 22 | 0 | 机械残留 |

改前只有两项亮红，而正是这两项决定了"像不像 AI"；改完两项归零，套话和方差几乎没动——**说明这两个常用指标本来就不是问题所在**。

同一份文档的下一轮（v3 → v4，只做"补图 + 改三句与表打架的解释"）：

| 指标 | v3（待改） | v4（改后） | 说明 |
|---|---|---|---|
| 套话命中 | 0 | 0 | 仍然不说明问题 |
| sd/mean | 0.51 | 0.54 | 仍然不说明问题 |
| images / 正文曲线词 | 0 / 16 | 1 / 1 | **这一轮唯一的重问题** |
| mechanism | 2 | 1 | 删掉 `signature of` 那句；`truncated tail` 那句留着 |
| placeholder | 1 | 0 | `x%→4x%` 换成 20 K → 0.7% → 3% |
| meta | 2 | 2 | 用户没让改（template / workbook sheets） |

这一轮**没有改任何数字**：图按同一份原始数据重算，改的只是"文字与物件的对应关系"。所以**修 AI 味不等于改数**——多数时候是让句子和已有的数、已有的图对上。

同一案例的 v1→v2 还修过三处**断言与表不符**，flavor_audit 一条都测不到，只有 consistency.py 会把相关句子和表行摊开，让人当场核对：

| 断言 | 表里的真实情况 |
|---|---|
| `The offset is nearly the same at every temperature` | Table 6：+3.49 / +5.21 / +2.69 / −1.10，跨 6.2% |
| `Integrating … over 800–2500 nm gives the total exitance` | 该窗口只覆盖 69.7–69.9%，表 5 的 E_T 隐含 ÷0.70 |
| `the transfer function K(λ) of Table 1` | Table 1 只有 I(A) / T(K) |

### 怎么回答"AI 味重吗"

不要给单一分数或"AI 概率"。按层给判断，每层引一句原文，最后区分四类东西：

1. **AI 写的**（论证 / 叙事）——要改；
2. **模板 / 翻译腔**（不是 AI，但一样像机翻）——问用户要不要改，别擅自改；
3. **数据**（同一次实验）——不是问题，不要动；
4. **与表 / 符号 / 引用矛盾的断言**——单列，最先修。它不是文风问题，但它是"作者没看过数据"的最硬证据。

**按节给分，不给总分。** 同一份报告里各节可以差 20 分：`封面 2/10、原理 4/10（翻译腔）、步骤 3/10（讲义直译）、数据 5/10、讨论 9/10、附录 3/10`。这样用户知道该改哪一节，也知道不必动哪一节。

**短答题反过来：给一个总分，但必须附三条撑起它的信号。** 用户问"这个答案 AI 味重吗"，要的就是一个能比的数。`8.5/10` 单独看没用，`8.5/10，因为成对破折号 + 倒装 + 两段同骨架` 才能用。分数是排序工具，信号才是修改清单。

**盲评有用，但别信它的数字。** 找一个没看过上下文的读者读一遍：他指出的句子值得看，他给的分只是印象，他推断的事实要复核。只把正文给他、不给表格时，他会得出"这些表是空的"之类的错误结论——那是抽样方式的问题，不是文档的问题。

典型回答："句子层不重（0/38 套话、方差像人），篇章层明显：六条讨论同一模子、每处偏差都被当场解释掉、正文没有过程；另外有三句话和表里的数对不上，那个比文风更先要修。"

## 4 论证层：四种泄漏 + 改写配方

| 泄漏 | 本次原文 | 改法 |
|---|---|---|
| 预先辩护 | `so the tail correction cannot explain the remaining 2.6% spread` | 删。停在数字上：`The 2.6% spread in δ is dominated by K(λ) at the scan ends and by the temperature.` |
| 预先辩护 | `the integrated exitance rises by 44% ... while the fourth power ... rises by 41%` | 保留两个数，删掉后面的`which is the form in which the law is tested` |
| 预先辩护 | `The observed scatter ... is therefore no larger than the reading allows, and four points cannot separate ...` | 整句删 |
| 预防性反驳（对照式） | `...rather than at the filter changes` / `which points to … rather than …` / `does not by itself contradict the law` | 删掉对照词（rather than / does not by itself），只留观察。它在替一个没人提出的解释设防 |
| 元话语 | `which is the form in which the law is tested across temperatures` | 整句删。句子在描述论证本身，不在讲对象 |
| 统一三段式 | 6 条讨论全是"claim → number → caveat → verdict" | 打散；允许某条只有一句；删每条句尾的 `so the T4 law is verified` |
| 即时量化 | 每写一个数就顺手算 0.13%、70 nm、6% | 保留主数字，删只在辩护里用到的衍生量 |
| 机制填充 | `The deviations are largest where the transfer function changes quickly (filter junctions)` | 表 2 里 1000 nm 的偏差只有 1.2%，最大的在两端（800 nm 7.4%，1700–1900 nm 7.5–7.6%）。机制句必须能在表里指到那一行，指不到就删，不要把"听起来对"当依据 |
| 占位符代数 | `An error of x% in temperature gives about 4x% in the total exitance` | 换成实数：20 K / 2700 K = 0.7%，四次方后 3%，正好等于 2.6% 的离散。`x%`、`4x%`、`for some x` 都是模型替自己省事的写法 |
| 元话语（实验报告变体） | `in the units of the template` / `sheets 4–6 of the calculation workbook that accompanies this notebook` | 删。老师打不开你的 workbook，也不该需要它才能看懂正文；"按模板单位"是给自己看的备注，不是报告内容 |
| 语域断层 | 操作段 `Establishment of...` / `Energizing heats the lamp`，分析段流利英文 | 统一成一种口吻；不要一半模板一半模型 |

**改写三原则**：
1. 删句子，不删数字。
2. 停在事实上，不要停在判断上。
3. 一条只写一句也可以。

**一个数是在描述对象，还是在替结论辩护？** 删掉它，结论还剩内容 → 它是证据（留，如 44%/41% 的 T⁴ 对比）；删掉它，结论要靠它才站得住 → 它是辩护（删，如 70 nm / 6% 的读数论证）。这条比"保留主数字"更可操作。

verdict 句（"the law is verified"）不是全删：结论段留一句可以，正文每条都留不行。

### 补图：一次修改顶十句润色

触发条件：`flavor_audit.py` [6] 报 `no image in the file, yet the prose talks about curves/plots N times`。这时改句子是隔靴搔痒，读者要的是那张图。

1. **图要回答正文那句话。** 本案例第 IV 节第 1 条在说"实测是否跟着同温度的理论走"，所以画三条实测谱（K 修正、1400 nm 归一，实线）对同温度 Planck 曲线（虚线、同色），而不是把原始读数画出来看看。
2. **图与表同一口径。** 图的管线要和生成表格的脚本一致；不一致就**在图注里声明**。本案例图用原始扫描 + K(λ)（与计算底稿同管线），表 2 的数字来自另一条管线，800 nm 处 1.32 vs 1.355 差 2%——图注写明归一化口径，且正文只用"±2% / 5% 以上"这类能同时成立的措辞。
3. **没有 matplotlib 时用 PIL。** 2× 超采样再 LANCZOS 缩回；字号换算 `px = pt/72 × 图宽px ÷ (图宽cm/2.54)`（15 cm 宽、2200 px ≈ 372 dpi，9 pt ≈ 46 px）；字体用 Times New Roman 对齐正文；图内不放标题，标题交给图注。
4. **python-docx 插入。** `fig_p = doc.add_paragraph()` → `fig_p.add_run().add_picture(png, width=Cm(15))` → `anchor._p.addnext(fig_p._p)` 搬到正文位置；图注单独一段，套已有 caption 的格式（本案例 9.5 pt 斜体居中、段前 3 pt / 段后 11 pt）；图段设 `keep_with_next`，别让图和图注分页。
5. **验收。** `len(doc.inline_shapes) == 1`；页数没变（本案例仍 5 页）；图与图注同页；渲染图里图内字号不小于正文的 7 成；正文里再加一句 `(Figure 1)` 指过去。

## 4.5 短答题：另一种文类，另一套判据

学生问"这个答案 AI 味重吗"，交上来的常常不是 docx，是两三段文字。这一文类里**第 4 层（叙事）和第 6 层（物件）不适用**——考试答案不需要时间戳和图；第 1 层照样 0 命中，第 3 层照样 sd/mean 0.4–0.5。七道密立根油滴短答题实测：前六层几乎全 PASS，唯一每次都亮的是第 7 层。

### 四条判据，按顺序问

| 顺序 | 问什么 | 七题实测 | 怎么改 |
|---|---|---|---|
| 1 | **句数 ÷ 分值** | 每题 6–9 句，对 2–4 分的题是 2–3 倍 | 先砍到 分值×1.5 句，再改句子 |
| 2 | **段落骨架是否重复** | 平衡法 / 动态法两段同骨架、同"报数量"收尾 | 第二段用一句 `starts the same way, but ...` 带过 |
| 3 | **每段末尾是否在收束** | 多数题每段末句都在"把话说满" | 删末句，停在数字或事实上 |
| 4 | **修辞** | 成对破折号 2 题、倒装 2 题、隐喻 1 题、三段式标记 3 题 | 见下表 |

**第 1 条是主判据。** 其余三条都建立在"答太多"之上——写得少就装不下镜像结构，也装不下修辞和收束句。所以顺序不能颠倒：**先砍，再改。**

判断"答太多"不用读完全文，看三样：句数是否超过分值×2；有没有出现题目没问的东西（第三种方法、数值估算、"能不能直接称"这类现实点评）；有没有把一句话的答案写成一段。

### 第 7 层的十个具体信号

| 信号 | 七题里的原文 | 改法 |
|---|---|---|
| 成对破折号 | `... — that every droplet ... — can only be established ...` | 改同位语或拆句。一句里两个破折号是 AI 指纹 |
| 倒装 | `Only under this spherical assumption are V = ... valid` | 还原语序：`V = ... is valid only if the droplet is a sphere` |
| 隐喻 | `Stokes' law ... is the bridge between the measurable kinematics and the unmeasurable geometry` | 换动词：`lets you get at the radius`。顺便：这句的 `unmeasurable` 本身是错的（半径能看见、只是量不准）——为了修辞牺牲准确是典型 AI 行为 |
| 对偶 | `the measurable kinematics and the unmeasurable geometry` | 删一半，只留一个说法 |
| 三段式标记 | `The fundamental reason is ... / In addition ... / Finally ...` | 删标记词，按内容自然分句 |
| 预告式列举 | `Four forces act on a droplet: gravity ..., buoyancy ..., drag ..., and ...` | 先报数量再列举是排版行为；直接写第一个力 |
| 平行 if 排比 | `if qE < ... ; if qE = ... ; if qE > ...` | 拆成三个独立短句，句长故意不齐 |
| 括号补充 | `keeps the radius (and hence the charge) stable` | 括号里那句是给自己加的戏，删 |
| 主动推荐 | `is therefore the recommended procedure` | 降级为 `is the version usually used in practice` |
| 自造完美数字 | `3.24 = 2e and 4.88 = 3e` 两个数严丝合缝指向 1.6 | 举例子要带毛刺：`a charge of about 3.2×10⁻¹⁹ C` |

### 模式 C 的改写示例

规则见 §2 第 10–12 条，这里给一段对照。每个数字、每条公式、每个结论原样保留，只改句法、句序、句长、连接词。

| 原 | 改 |
|---|---|
| `... Eliminating K removes the unknown mass and yields q from purely macroscopic quantities — voltage, plate separation, fall and rise times, viscosity and density — so a microscopic charge becomes measurable.` | `... Eliminating K removes the unknown mass, and q then follows from quantities we can actually measure: the voltage, the plate separation, the fall and rise times, the viscosity and the density. That is why a charge this small can be measured at all.` |

改动清单：拆长句（3 句→5 句）、删破折号改冒号、`so a microscopic charge becomes measurable` 的对偶改成 `That is why ... at all`。

### 让句子变回人味的五个动作

1. **长句拆短，句长故意不齐。** 原来每句 25–30 词，改完 12 / 31 / 8 / 22。
2. **抽象名词化改回动词。** `is the bridge between X and Y` → `lets you get at X`；`the continuum assumptions break down` → `stops being accurate`。
3. **把比例关系翻译成人话。** `m ∝ r³` 后面补半句 `double the radius and you get eight times the mass`。AI 倾向于继续往上抽象，人倾向于往下举个例子。
4. **停在事实上，不停在判断上。** 删掉 `so it must be applied` / `which is why` / `is the recommended procedure`，让句子以数字或现象结尾。
5. **允许段落突然结束。** 一段两句话就够，不要每段都补一句完整性声明。

### 校准（两组配对，脚本实测）

| 指标 | q1 改前 | q1 改后 | q7 改前 | q7 改后 |
|---|---|---|---|---|
| 句数 | 7 | 5 | 8 | 9 |
| 第 7 层信号 | 2 | 1 | 6 | 2 |
| 第 2 层 meta | 1 | 0 | 0 | 0 |
| 第 3 层 sd/mean | n/a（句数不足） | n/a | 0.39 | 0.42 |

**这张表最重要的信息是两列之间不一致。** q1 的问题是长度：7 句砍到 5 句，信号顺带从 2 掉到 1。q7 的问题是修辞：信号 6→2，但句数 8→9——拆句反而多了一句。所以"先砍再改"不是二选一，是**两遍**：第一遍删内容降句数，第二遍拆句法降信号。只做一遍，另一个指标不会动。

**第 2 层是 0 也要记住**：q7 改前 defence 0 / meta 0，按第 2 层完全干净，照样是七题里分数最高的两版之一。短答题里 AI 不做防御，它做的是"把知道的都倒出来"——防御句是论文的毛病，不是答题的毛病。

**最难删干净的是 closure。** q1 改后只剩 1 个信号，就是句尾那句 `so in practice it looks as though it falls at a constant speed`。"顺手补一句现实意义"听起来完全合理，所以改稿时最容易漏掉；判据是问一句"删掉它，前面的物理还成立吗"——成立就删。

### 验收

改完重跑 `--genre answer --marks N`：第 7 层降到 `INFO` 或 `PASS`（≤2 个信号）、无镜像段落、句数 ≤ 分值×1.5。只降字数不改句法，信号原地不动；只拆句不砍内容，句数反而上升。

## 5 叙事层：把"报告"改回"记录"

- **实验还没做、数据段留白的预填稿，第 4 层必然 REVIEW，不要改。** 判据是文档里有没有留白的数据段：`III. Experimental Data` 后面空着、表还没填，说明时间戳要等做完实验才有。这时候补时间戳就是编记录 —— 一个 `clock 0` 的预填稿不是缺陷，是还没到那一步。等数据填进去再跑一次。
- 先找真实过程：仪器文件头的保存时间、表格里的采集设置、重测记录、备注。
- 本案例可用的事实：7 个 `.ht` 文件保存时间 11:36–12:06、2 nm 步长、851 点、两次累加、增益 3、负高压 3。
- **没有记录的一律不写。** 本案例差点写"约 5 min 稳定""基线约 2000、扫描前扣除"——那是举例时编的，不是记录；最后只写了文件头里有的。
- 缺原因就写"保留在原始记录"，并告诉作者"这里缺一句原因，你补"。

一个 notebook 的叙事层应该是：几点开始、等了多久、哪条重测过、哪次饱和了。没有这些，它就是一份报告。

## 6 词汇层：最弱的一层

中文：

| 模型会写 | 改成 |
|---|---|
| 首先…其次…最后… | 直接分点，或按时间顺序平铺 |
| 综上所述 / 总而言之 | 删掉，最后一段自然收尾 |
| 值得注意的是 / 需要指出的是 | 删掉这四个字，后面的句子原样保留 |
| 不仅…而且… 连用 | 拆成两句 |
| 为…奠定了坚实基础 / 提供了新的思路 | 删。实验报告不需要升华 |
| 每段三句、每句等长 | 保留原稿的长短不齐 |
| 全角破折号 "——" 当万能连接 | 改逗号、冒号或句号 |
| 加粗引导词开头的行（"**结论：** …"） | 正文里不要；真正的列表可以用 |
| 把口语改成公文（"电流调到 2.5 A" → "将工作电流设定为 2.5 A"） | 保留作者原话 |

英文（实验报告常见）：

| 模型会写 | 改成 |
|---|---|
| It is worth noting that / It should be noted that | 删 |
| Furthermore / Moreover / Additionally 机械串联 | 直接并列，或拆句 |
| delve into, crucial, pivotal, robust, leverage, comprehensive | 换普通词：look at, main, key, steady, use, full |
| 三连排比（fast, accurate and reliable） | 说两个，或说清哪个最重要 |
| 每段主题句开头 + 总结句结尾 | 允许段落突然结束 |
| 过度 hedge（may potentially suggest） | 一个 hedge 就够 |
| 成对破折号 `... — gloss — ...` | 同位语、括号，或拆成两句 |
| 倒装 `Only under X are Y valid` | `Y is valid only if X` |
| 隐喻 `is the bridge between` / `is the language of` / `is the only way to` | 直接说它做什么 |
| 三段式标记 `The fundamental reason` / `In addition` / `Finally` | 删标记词，按内容分句 |
| 预告式列举 `Four forces act: a, b, c, d` | 直接写第一个，别先报数量 |
| 主动推荐 `is therefore the recommended procedure` | 降级成"通常这么做" |

命中说明"像模板"，不说明"是 AI 写的"；0 命中也不说明干净。**后六行不是词，是句法**——它们不靠词表命中，靠 `flavor_audit.py` 第 7 层的结构规则，换同义词换不掉。

## 7 结构层：补缺损，不补内容（模式 A）

| 情况 | 做 | 不做 |
|---|---|---|
| 有表体没表题 | 补一行 `Table 7. …` | 顺手补一段分析 |
| 有 "3. Verification…" 没 "4." | 补节标题 + 一句引导 | 补一整节论述 |
| 表格有空列空行 | 删列、删行、或并格 | 填 "N/A" 把格子凑满 |
| 作者没写结论 | 保留没有结论 | 加"综上，本实验验证了…" |
| 期刊/老师没要求的小节 | 不建 | 建"误差分析""改进建议" |

新写的标题和表题，用作者正文里已经出现过的词。作者一直说 amplitude，就别在表题里换成 magnitude。

**有一种结构重合是正当的**：同一小组共用数据、老师要求统一模板，或者用户明确说"就按合作者那版排"。这时表格行文、表序、表头措辞对齐没问题，但要守住两条：① 只对表格和版式，caption 和 heading 仍然用自己的话；② 交付时说明这是组内商定的呈现，不是文字上的借用。

> **实测：模式 A 里最容易泄漏的是 caption 和 heading，不是正文。** 因为"学版式"时眼睛就停在那些短句上，回头写标题会不自觉复述。上一次案例里唯一一段高重合（67%）就是一条表题。

## 8 文件层：Office 指纹

- **python-docx 新建文档的残留**：`docProps/thumbnail.jpeg`（资源管理器里看到的缩略图是模板图）、`styles.xml` 里未使用的 Courier 潜在样式、中文文档的 `docGrid linePitch="312"`。
- **字体混用是最大破绽**：一份文档里同时出现 Segoe UI + 仿宋_GB2312 + 宋体 + Times New Roman，说明是拼接的。统一成一种西文 + 一种中文。
- **缺字回退**：用了本机没装的中文字体，导出 PDF 会被替换。上一次案例里 仿宋_GB2312 被换成 Symbol，`Experimental Principles` 渲染成 `Εξπεριμενταλ Πρινχιπλεσ`。**必须看渲染图才发现，看源文件看不出来。**
- **残留强制分页符** → 每页底部大段空白。页码用 `w:fldSimple PAGE` 字段，不要手打数字。
- **脚本生成文档的不可见字符**：U+2060（word joiner）常被排版脚本插在数字范围前（`800–2500`）。Word 里看不见，PDF 导出会变成 `800 –2500` 的空隙；查重和文本抽取会当成异常字符。`flavor_audit.py` 第 5 层会数出来。

## 9 docx 手术与版式验证（模式 B 必看）

- **优先做 run 内等值替换，不要整段重建。** 定位目标 run，`assert run.text == old`，只换文本——上下标、字体、字号全部原样保留。只有需要改变上下标归属时，才抓 rPr 模板（普通 / 上标 / 下标各一份）重建；不要 `p.clear()` 后直接 `add_run()`。
- **断言失败先看 `repr()`。** 最常见的两个原因：run 以空格开头（`' law is verified'`），或范围里藏着 U+2060（`'2\u2060–4'`）。别为了过断言去放宽比较，逐字打印后再改。
- 改完必查 `T⁴`、`×10⁻¹⁴`、`W·mm⁻²·K⁻⁴`、`λmax` 这类 run 是否还是上 / 下标。
- **表格逐格比对**：改前改后把每个 cell 的 text 取出来 diff；允许的差异只有你确实改过的单元格和不可见字符。
- **包装层面比对一次哈希。** 改完把 docx 的 zip 各部件哈希与改前比：正常只有 `word/document.xml` 变化（加图时多一个 media 文件）。别的部件变了，说明有工具动过样式或编号，要退回。
- **重新导出 PDF 用同一引擎**（本案例是 LibreOffice 26.8）。页数、分页位置、孤行都要看渲染图：
  - 文字变短会把分页边界往前挪，可能留下 `(Table 8).` 这种孤行；重排一句即可。
  - `missingFonts: Courier` 可能只是未使用的潜在样式；查 PDF 里是否真的引用（本案例两版都没有）。
  - **LibreOffice Kit 不覆盖已存在的输出**：报 `EEXIST: file already exists`。先删旧 PDF 再导出，或换新文件名——不要误判成文档坏了。
- 清 U+2060 会让 PDF 里 `800 –2500` 的空隙消失，这是顺带的好处。

## 10 量化验收：三个脚本，三个问题

| 脚本 | 回答的问题 | 输出 |
|---|---|---|
| `flavor_audit.py` | 这段文字像不像模型写的？ | 七层 PASS / REVIEW / STRIP + 具体句子；`--genre` 选文类（notebook / report / answer / paper / thesis / talk），该文类不适用的层标 `n/a`；`--marks N` 另给句数预算 |
| `consistency.py` | 说的和表对不对得上？物件齐不齐？ | 近常数行的散布、无出处的数、符号、交叉引用、缺失图/表、占位符 |
| `overlap.py` | 这段文字是不是从参考稿来的？ | 重合度、逐字相同串、同名标题 |

三个都要跑，但**不要混**：重合度高是抄参考稿的风险；论证 / 叙事亮红是 AI 写的风险；断言与表不符是"写句子的人没看数据"的风险——三类问题三种修法，改一类不会带走另一类。

**没有 python-docx 也能跑。** 三个脚本都带 `scripts/docxfallback.py`（纯标准库解析 `word/document.xml`），`from docx import Document` 失败时自动切换：`flavor_audit.py` 不再降级成 txt（第 5/6 层照出），`consistency.py` / `overlap.py` 也不再直接拒收。实测：无网络、pip 装不上 python-docx 的机器上，三个脚本对同一份 .docx 都能出完整报告。差异只有一处 —— fallback 只读正文、表格与 `w:drawing`，不解析页眉页脚和批注。

```bash
python scripts/consistency.py 我的定稿.docx
python scripts/overlap.py 我的定稿.docx 参考稿.pdf --baseline 我的原稿.docx
python scripts/flavor_audit.py 记录本.docx                     # 默认 notebook
python scripts/flavor_audit.py 实验报告.docx --genre report
python scripts/flavor_audit.py 课程论文.docx --genre paper
python scripts/flavor_audit.py 开题报告.docx --genre thesis
python scripts/flavor_audit.py 答辩稿.txt --genre talk
python scripts/flavor_audit.py 答案.txt --genre answer --marks 4
```

**consistency.py 怎么读**（六组输出，只做提示，判断仍在人）：

| 组 | 用法 |
|---|---|
| `[1] prose claims` | 文中所有"比较 / 恒定 / 总量"句。逐条问：它说的量在 `[2]` 里是哪一行？下面单列的 mechanism 句同理——那个"因为"在表里指得到吗？ |
| `[2] near-constant rows` | 散布 ≤10% 的表行才列出来，因为只有这些行配得上"恒定"的说法。`δ` 行 2.6%、`λmaxT` 行 6.2%——`nearly the same` 对着 6.2% 就是硬伤 |
| `[3] numbers not in tables` | 文中出现、表里找不到的数。派生量（平均值、偏差）正常；既非派生又无出处的，是编的 |
| `[4] naming sentences` | `here it is written X`、`written as X`、`记为`——同一量两套符号的残留都藏在这里。新版会把"声明改成 X、正文却仍用 Y"直接算出来（本案例 δ 6 次 vs σ 3 次，立刻报 leftover） |
| `[5] table inventory + cross-ref` | 每张表的表头；`of Table N` 里提到的希腊符号若不在该表，直接报 CROSS-REF（本案例 `K(λ) of Table 1` 就是这样被抓到的） |
| `[6] artefacts & placeholders` | 图/表引用有没有对应物件（`images 0` 却讲曲线、`Table 9` 却没这张表）；`x%` / `4x%` 占位符。这一组 PASS 才算"读者能看到你说的一切" |

**overlap.py 校准值**，先用它读懂输出：

| 情形 | 正文平均重合 |
|---|---|
| 拿自己和自己的原稿比（同一批文字） | **83%** |
| 完全重写过的同题文本 | **0.6%** |
| 照参考稿写了 1 条表题 | **3%** 左右 |
| 把老师发的讲义压缩成「原理」一节（保留原句） | **40–55%** |
| 抄了几段 | 15% 以上 |

判据：

| 指标 | 独立 | 可疑 | 要处理 |
|---|---|---|---|
| 正文散文（≥60 字符段落）平均重合 | ≤1% | 3–15% | >15% |
| ≥25 字符逐字相同串 | 全部出自我的原稿 | 混入 1–2 条参考稿的 | ≥3 条 |
| 节名 / 表名 / 表序 | 与参考稿不同 | 部分同名 | 全部同名同序 |

**`--baseline` 不能省。** 上一次案例：原稿 0.6%、定稿 3.2%，差值 2.6 个百分点全部来自一条新写的表题——没有基线这个结论出不来。

**「照讲义抄」不是 AI 味，但仍然是风险，两件事要分开报。** 实测一份实验记录本：原理节平均重合 48.4%、≥25 字符逐字串 20 条、最长 81 字符（`open the oil-feed control switch and spray a small amount of oil mist into the`），而句子层干净得不像机器写的（[2] 全 0、sd/mean 0.91、套话 0 命中）。原因是作者把老师发的讲义压成了记录本的原理段 —— 老师拿讲义一对就能看出整句搬，但这跟"是不是 AI 写的"无关。这种文档的结论要写两句：「AI 味轻；但和讲义重合 48%，最长 81 字符照搬，改法是换说法，不是改句式。」用户可能只让你改后者，那就别动句子结构。

## 11 陷阱表（实测）

| 坑 | 现象 | 处理 |
|---|---|---|
| 套话表 0 命中 | 误判为"没有 AI 味" | 看论证层和叙事层；套话只是辅助 |
| 句长方差大 | 误判为"像人写的" | 方差只说明节奏，不说明论证结构 |
| 数字全对 | 误判为"不是 AI 写的" | 数字是证据，不是文风 |
| 短答题前六层 PASS | 误判为"不像 AI" | 这一文类跑 `--genre answer`；主判据是第 7 层 + 句数/分值比 |
| 把好答案判成"叙事层缺失" | 考试答案本来就没有时间戳 | `--genre answer` 把第 4/6 层标 n/a；n/a 不是问题 |
| 只换同义词 | 改完第 7 层数字一动不动 | 修辞是结构问题；拆句、删标记词、还原语序才动得了 |
| 答案比题目要求长三倍 | 误以为"答得全 = 答得好" | 句数 ≈ 分值×1.5；先砍再改 |
| 为修辞牺牲准确性 | `the unmeasurable geometry`，而半径其实能看见、只是量不准 | 修辞盖过事实的地方，先修事实 |
| 清 run 重建 | 上下标（T⁴ / λmax）丢失 | 先抓 n / sup / sub 三种 rPr 模板再重建 |
| 文字变短后重导出 | 分页边界移动，出现 `(Table 8).` 孤行 | 看渲染图，重排该句或调段长 |
| `missingFonts: Courier` | 导出报警但 PDF 里没有 Courier | 查 PDF 字体引用；可能只是未使用样式 |
| U+2060 | Word 不可见，PDF 里成 `800 –2500` 空隙 | 全清；清完重导出 |
| 短串覆盖率 | 短于 shingle 长度的段（标题）算出 0% 或 100% | 只统计 ≥60 字符段落，短串单独列 |
| `difflib` autojunk | 长字符串 `ratio()` 假低（上一次报 44.5%，实际远高） | 用 `autojunk=False`，或干脆用 shingle |
| PDF 抽不出字 | Identity-H + 子集字体，每个字形单独 `Tj` | 按 ToUnicode CMap 还原，`scripts/pdftext.py` |
| 只比 docx 正文 | 漏掉表格雷同 | 表格单元格文本也进语料 |
| 把数字相同算抄袭 | 同一次实验必然相同 | 分开统计，不并入文字重合 |
| 结构借用拖数据 | 补了 mean 列 / 偏差行，算出来的数也跟着和参考稿一样 | 结构借用要单独说明，或换个呈现方式 |
| 句子很顺但和表矛盾 | `nearly the same` 对着 6.2% 的散布；`gives the total` 对着 70% 的覆盖 | `consistency.py` [1]×[2]；重写该句，删形容词没用 |
| 机制句听起来对 | `deviations are largest at the filter junctions`，而表里 1000 nm 只有 1.2% | `flavor_audit.py` [2] mechanism；在表里指到那一行，指不到就删 |
| 占位符 x% / 4x% | `An error of x% ... gives 4x%` | `flavor_audit.py` [2] placeholder；换成实测数字（20 K→0.7%→3%） |
| 正文描述曲线、文件没图 | 4 处曲线描写、`inline_shapes = 0` | `flavor_audit.py` [6]；补图（§4 补图），比改句有效 |
| 图与表两套口径 | 图 800 nm = 1.32，表 = 1.355 | 同管线重算，或图注声明；别默认老师不会对 |
| 一个符号只出现一两次 | σ 与 δ 指同一个量，还留着 `here it is written σ` | `consistency.py` [4]；统一符号，删 naming 句 |
| 交叉引用张冠李戴 | `K(λ) of Table 1`，而 Table 1 只有 I(A) / T(K) | `consistency.py` [5]；按表头逐条核对 |
| 盲评只给正文 | 评审说"这些表都是空的" | 连表格一起给，或声明"表里有数，别评表格" |
| 导出目标已存在 | LibreOffice `EEXIST: file already exists` | 先删旧 PDF，或换输出名 |
| run 替换断言失败 | run 以空格开头，或范围里含 U+2060 | `repr()` 打印后再改，别放宽断言 |

## 12 交付前清单

- [ ] 场景 A / B / C 已判定；A/B 和上一版逐段 diff 过，只动嫌疑段
- [ ] `--genre` 选对了（§ 适用范围表）；标 `n/a` 的层没有被当成问题
- [ ] 模式 A：正文每个字都能在作者原稿里找到，或是我新写的过渡句（越少越好）
- [ ] 模式 A：`overlap.py` 三档指标都在"独立"列；≥25 字符逐字相同串全部来自作者原稿
- [ ] 模式 B：`flavor_audit.py` 的 defence / meta 归零，verdict 只留在结论
- [ ] 模式 B：叙事层至少补进真实时间 / 设置；没有记录的地方明确标注，没有编
- [ ] 有表：`consistency.py` 无 CROSS-REF；`[1]` 每个"恒定 / 总量"句都能在 `[2]` 找到对应行，且散布与措辞相符
- [ ] 有表：`[3]` 里每个无出处的数，要么能被本文数据推出来，要么删掉
- [ ] 物件齐全：`flavor_audit.py` [6] 为 PASS；正文引用的每张图 / 表在文件里都存在，且图注 / 表题都在
- [ ] 没有 `x%` / `4x%` 占位符；每个 mechanism 句都能在表里指到对应的行
- [ ] 补的图与表同口径；不同口径已在图注里写明（本案例 2%）
- [ ] 符号统一：同一量只有一个符号，没有 `written as` / `记为` 残留
- [ ] 盲评意见逐条复核过；评审没看到的表，不能当证据
- [ ] 数字与原稿逐格脚本比对过，不靠眼睛
- [ ] 上下标 run 未丢；表格除有意改动外零差异
- [ ] U+2060 等不可见字符清零
- [ ] [5] 字体家族 ≤2、`bold lead-ins` = 0（markdown 的 `**标签**` 已去掉，文字没改）
- [ ] 预填稿（实验未做、数据段留白）的第 4 层 REVIEW 已确认是"还没到那一步"，没有为了消红去编时间戳
- [ ] 同引擎重导出 PDF，逐页看过图（分页、孤行、缺字）
- [ ] 短答题：句数 ≤ 分值×1.5；第 7 层 ≤2 个信号；无镜像段落
- [ ] 短答题：没有 `The fundamental reason` / `In addition` / `Finally` 这类三段式标记
- [ ] 全文搜过 `—`（有没有成对出现）和 `;`（每 100 词 <1.5 个）；这两个字符是最浓的 AI 味
- [ ] 内容 / 物理层面的问题单独列给用户，没有被顺手改掉
- [ ] 给作者一份 diff，说明改了哪几句

## 13 配套

文档本身的读写走 `office-docx`，导出走 `office-export-pdf`，逐页看图走 `office-render`。
本技能只负责"内容像不像作者本人"，不重复那三个技能的 OOXML 细节。

## 14 一页复盘：五类错误，五种修法

| 错误 | 本案例的样子 | 怎么修 | 哪个脚本先发现 |
|---|---|---|---|
| 论证泄漏 | 4 句 defence、1 句 meta；每条讨论以 `so the T4 law is verified` 收尾 | 删句子，停在数字上 | flavor_audit [2] |
| 断言失配 | `nearly the same`（6.2%）、`gives the total`（70%）、`K(λ) of Table 1`；机制句 `filter junctions`（表里 1.2%） | 重写或删句，不能只删形容词 | consistency [1]/[5] |
| 物件缺失 | 4 处描述曲线、`inline_shapes = 0`；`Table 2 and the Planck curves` 无处可看 | 用同一份数据补图，正文加 `(Figure 1)` 指过去 | flavor_audit [6] |
| 叙事为零 | 0 个时间戳，正文像成品报告 | 补仪器记录里的真实时间 / 设置 | flavor_audit [4] |
| 修辞泄漏 | 成对破折号、`Only under X are Y valid`、`is the bridge between`、两段同骨架、每段末句收束 | 拆句、删标记词、还原语序；先砍长度 | flavor_audit [7] |

长文档的优先级：**先补物件 / 修断言，再删论证，最后补叙事。** 物件缺失和断言错误都让读者三分钟看出"写的人没看过数据"；论证删多了只是少几句话；叙事最花时间，且常常没有记录可补，宁可标"无记录"。

**短答题的优先级正好相反：先砍长度，再动修辞。** 因为多数修辞信号是"写太多"的副产物——答到 分值×1.5 句时，装不下镜像段落、装不下三段式标记、也装不下那句"所以实际测量中……"。只改修辞不砍长度，第 7 层会一直亮着。

一句话：**AI 味最轻的版本，不是句子最短的版本，是每句话都能对上数据、每个图都能被正文指认、每个过程都能对上记录的版本。**

短答题是例外：那里 AI 味最轻的版本，就是**最短**的版本。判据只有一条——写够分数该给的，然后停。
