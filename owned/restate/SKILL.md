---
name: restate
description: Repeat what the user says to ensure that everyone has a consistent understanding
version: "1.0.1"
---

当用户提出需求或要求进行 BugFix，应遵循以下步骤：

1. [必须] 复述用户的需求/问题，确保理解一致
2. 探索代码库，深刻理解它的工作原理、功能以及所有细节。
3. 根据你的探索结果，[必须] 再次复述我的需求/问题，确保理解一致
4. 提供解决方案的初步想法
5. 实现解决方案
6. 新增 or 更新 or 删除测试, 进行测试验证，保证测试覆盖率 > 85%.
7. 构建应用，并修复构建错误
8. 文档更新

若用户多次提出 “还是无法解决”、“问题还存在”，请直接重构代码。

