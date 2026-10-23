# Changelog

## 1.3.0 — 2026-10-23

这一版来自一份真实的中英双版密立根油滴实验报告：文字层几乎全 PASS，但脚本在中文题注、公式排版表、字体名、页脚页码上产生了 8 类误报。全部修掉，并补了回归测试和实验报告案例。

### Fixed

**`flavor_audit.py`**

- 中文 `表 N` / `图 N` 题注和引用现在能识别，支持 `A1` / `A2`。
- `content_tables()` 跳过 1 行无边框公式排版表；`[6]` 不再把公式表算成“无题注表”。
- 以 `Table` / `Figure` / `表` / `图` 开头的题注段落不再计入 bold lead-ins。
- 中文 `我` / `我们` 计入第一人称。
- 编号步骤（`^\d+[.、]`）和题注不参与镜像段检测；少于 3 句的段不参与。
- 倒装正则改为大小写敏感，小写 `only` 不再误报。

**`layout_audit.py`**

- `family_of()` 归一 `TimesNewRomanPS-BoldMT` → `TimesNewRoman`；`OpenSymbol` 归为数学字体。
- 表头加粗和 12 pt 以上标题不计入正文加粗。
- `is_page_number_line()` 识别“标题 + 页码”页脚；排除 `Table 2`。
- 末页留白 55% 放行（阈值 56%）。

**`consistency.py`**

- 表题注支持中英文、表上方或下方、`A1` / `A2`。
- 跳过公式排版表；`表 N` 引用计入交叉引用。

### Added

- `tests/test_smoke.py`：16 个回归用例。
- `SKILL.md §15`：实验报告专用清单 + 密立根油滴报告实测。
- README 的 v1.3 更新说明。

### Changed

- `SKILL.md` 版本号 1.3.0，`verified` 更新到 2026-10-23。

## Earlier versions

见 `git log --oneline`。
