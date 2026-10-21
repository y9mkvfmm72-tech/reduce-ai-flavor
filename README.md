# reduce-ai-flavor · 去 AI 味

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

> 更适合中国大学生宝宝体质的去 AI 味 skill —— 让你的报告不再漏洞百出。

把 AI 参与过的学生文档改到**看不出是 AI 做的**。覆盖实验记录本、实验报告、实习报告、课程论文、读书报告、文献综述、开题报告、毕业论文、实验问答题、汇报与答辩讲稿 —— 凡是署名交给老师、助教或答辩委员会的东西。

---

## 为什么需要它

常见的"去 AI 味"做法是替换套话：把「值得注意的是」删掉、把「综上所述」改掉。这类做法基本无效。

在本技能沉淀的原始案例里，一份 43 条套话的扫描结果是 **0 命中**，句长方差也看起来很像人写的，但文档仍然一眼 AI。真正的泄漏在别的地方：

- **论证层**：每条讨论都以「所以 T4 定律得到了验证」收尾，先自我防御再给结论
- **断言层**：正文说「几乎相同」，自己的表算出来差 6.2%；正文说「积分得到总量」，表里只占 70%
- **物件层**：正文 4 处描述曲线，文件里 `inline_shapes = 0`，一张图都没有
- **叙事层**：0 个时间戳，正文像成品报告而不是过程记录

所以这个技能的判据不是"句子像不像 AI"，而是**每句话能不能对上数据、每个图能不能被正文指认、每个过程能不能对上记录**。

---

## 七层泄漏诊断

| 层 | 查什么 |
|---|---|
| 1 词汇 | 套话、连接词堆叠、四字格 |
| 2 论证 | 预先防御、自造机制、占位符代数 |
| 3 节奏 | 句长分布、段落骨架重复 |
| 4 叙事 | 有无时间戳、有无过程、像记录还是像报告 |
| 5 文件 | Office 元数据指纹、修订痕迹、不可见字符 |
| 6 闭合 | 正文断言与自己的表格是否对得上；正文提到的图是否存在 |
| 7 修辞 | 成对破折号、三段式标记、每段末句收束、镜像段落 |

不同文类命中的层不一样，所以有**文类路由**：实验记录本看重 4/6 层，短答题看重 3/7 层，课程论文看重 2/5 层。`flavor_audit.py --genre` 用来选文类。

---

## 三种修法（先判场景，再动手）

| 模式 | 前提 | 允许做什么 |
|---|---|---|
| **A** 只碰过版式 / 翻译 | 句子能逐字对回原稿 | 文字回到原稿，只动版式 |
| **B** 写过正文 | diff 出整段新文字 | 允许删 / 压 / 降调，**不许新增事实** |
| **C** 短答题 | 2–4 分一题 | 只动句法，先砍长度再动修辞 |

铁律：**只有 diff 出来的段落才是嫌疑段。作者自己写的段落，一个字都不要顺手"润色"——润色本身就是 AI 味。**

模式 B 的前提是数据、实验、结论都是作者自己的，只是措辞由机器起草。如果整份文档连内容都不是作者的，本技能不适用。

---

## 三个量化脚本

全部**只读**，零第三方依赖（纯标准库，自己解析 docx / pdf），输出的是"具体哪句话有问题"，不是分数。

### flavor_audit.py —— 这份文档像不像模型写的

```bash
python scripts/flavor_audit.py 文档.docx
python scripts/flavor_audit.py 文档.docx --tables        # 连表格单元格一起扫
python scripts/flavor_audit.py 文档.docx --genre 短答题   # 选文类
```

逐层打印命中数和**携带该模式的原文句子**，方便直接删或压。

### consistency.py —— 说的和表对不对得上

```bash
python scripts/consistency.py 定稿.docx
python scripts/consistency.py 定稿.docx --max-claims 15
```

输出六张清单：正文断言、近似恒定的数值行及其相对偏差、正文里表格中不存在的数字、命名句与一次性希腊符号、表格清单与所有「of Table N」交叉引用、正文需要但文件缺失的图。

### overlap.py —— 像不像抄参考稿

```bash
python scripts/overlap.py 我的定稿.docx 参考稿.pdf --baseline 我的原稿.docx
```

给三个数：散文重合率（25 字 shingle）、逐字相同的句子、共享小标题。`--baseline` 实际上不是可选项 —— 它在你最初那版稿子上跑同一个测量，用来区分"这个数字是你改出来的"还是"本来就长这样"。

实测：正文散文与参考稿重合 **3.2% → 0.6%**。

### pdftext.py —— 顺手带的 PDF 取文

```bash
python scripts/pdftext.py input.pdf [output.txt]
```

处理 Word / LibreOffice 导出的 Identity-H 子集字体，走 `/ToUnicode` CMap 还原 Unicode。

---

## 目录结构

```
reduce-ai-flavor/
├── SKILL.md                  # 主体：七层诊断、文类路由、改写配方、陷阱表、交付清单
└── scripts/
    ├── flavor_audit.py       # 像不像模型写的（1–7 层）
    ├── consistency.py        # 断言与表格/图是否闭合（第 6 层）
    ├── overlap.py            # 与参考稿的相似度
    └── pdftext.py            # 无依赖 PDF 取文
```

`SKILL.md` 是主体，脚本只是量尺。先读第 0 节判场景，别上来就跑脚本。

---

## 怎么用

**方式一：作为 Agent Skill 安装**

把整个目录放进你的 skills 目录即可，例如：

```bash
git clone https://github.com/y9mkvfmm72-tech/reduce-ai-flavor.git ~/.agents/skills/reduce-ai-flavor
```

WorkBuddy / Claude Code 之类的 agent 会自动读取 `SKILL.md` 的 `name` 与 `description` 字段，在你提到"降 AI 味 / 去 AI 感 / 像不像 AI 写的 / 查重 / 和参考稿太像"时触发。

**方式二：当文档读**

直接读 `SKILL.md`，里面的诊断清单、改写配方、陷阱表和交付前 checklist 都是可以手动执行的。

**方式三：只用脚本**

```bash
git clone https://github.com/y9mkvfmm72-tech/reduce-ai-flavor.git
cd reduce-ai-flavor
python scripts/flavor_audit.py 你的文档.docx
```

Python 3.9+，无 pip 依赖。

---

## 边界

- 它不生成内容，只判断和删改。写作本身不在范围内。
- 它不替你做实验、不替你编数据。断言对不上表的时候，改的是句子，不是表。
- 内容层面的错误会单独列给你，不会被"顺手改掉"。
- 它面向的是"作者本人写了内容、措辞被机器润过"的场景。整份文档都不是作者写的，那是代写，不适用。

---

## 配套

文档读写走 `office-docx`，导出走 `office-export-pdf`，逐页看图走 `office-render`。本技能只负责"内容像不像作者本人"，不重复 OOXML 细节。

---

## License

[MIT](LICENSE) © 2026 y9mkvfmm72-tech

可自由使用、修改、分发、商用，保留版权声明即可。
