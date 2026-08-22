# ACTION-06 核心推荐规则复核记录

- 复核范围：推荐引擎实际依赖的 7 条核心规则
- 复核方式：`Project Lead-authorized review / Codex-assisted`
- 核心放行结果：`PASS`
- ACTION-06 总体状态：`OPEN_REMAINING_REVIEW`

## 放行规则

| 规则 | 原始资料 | 复核要点 |
|---|---|---|
| `rule-A-plate_211` | A 第 1–2 页 | 211 份数、餐盘比例、食材示例和健康脂肪份量一致 |
| `rule-A-fat_loss_guidance` | A 第 4 页 | 300–500 kcal 缺口、蛋白质、糖油、进食顺序和饮水量一致 |
| `rule-B-food_substitutions` | B 第 5 页 | 三类食材替换份量与各替换组一致 |
| `rule-B-muscle_targets` | B 第 6 页 | 能量盈余、蛋白质、碳水和月增瘦体重一致 |
| `rule-B-muscle_timing` | B 第 6 页 | 训练前后、睡前时机及示例一致 |
| `rule-B-gi_categories` | B 第 7 页 | GI 边界和示例一致 |
| `rule-B-plate_321` | B 第 7 页 | 321 份数、餐盘比例、主食份量和进食顺序一致 |

## 安全边界

原 B 文档中的 `rule-B-fat_loss_targets` 含无法从源文件确定的比较符号，继续保持 `review_required`，减脂推荐改用无缺字且已复核的 A 第 4 页规则。页面其他段落存在缺字不等于本规则字段存在缺字；放行依据是逐字段对照及规则级 `unknown_glyph=false`，不能扩大为整页放行。

本地真实 HTTP 冒烟已经确认减脂、增肌、稳糖三种目标均返回 `ready`；缺目标、年龄范围不明确、过敏和肾病约束仍然 fail-closed。其余 73 条结构化事实不进入确定性推荐，继续由 ACTION-06 跟踪，不能宣称 80 条已全部复核。
