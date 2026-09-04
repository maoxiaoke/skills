---
name: restate
description: Repeat what the user says to ensure that everyone has a consistent understanding
version: "1.0.6"
---

当用户提出需求或要求进行 BugFix，应遵循以下步骤：

<restate_flow>
1. [必须] 复述用户的需求/问题，确保理解一致
2. 探索代码库，深刻理解它的工作原理、功能以及所有细节。
3. 根据你的探索结果，[必须] 再次复述我的需求/问题，确保理解一致
4. 提供解决方案的初步想法，这个过程中**如有必要(真的是你无法掌握方向的问题)**，使用 $grill-me 技能跟我进行沟通。
5. 若方案复杂，请等待我进行确认。但是这里要注意，一些很简单的任务**就不必询问**，你直接处理。
6. 实现解决方案
7. 不要写测试，我不要求测试覆盖率
8. [如有]清理前置错误或无用的代码逻辑
9. [如有]构建应用，并修复构建错误
10. [如有]文档更新
</restate_flow>

若用户多次提出 “还是无法解决”、“问题还存在”，请直接重构代码。

## 案例

### 方案设计
用户要求对某些**复杂**的方案进行设计时
1. use restate_flow 来理解当前设计， code is the first source of truth
2. 使用 $grill-me 对核心问题扩展理解，达成共识.
3. 生成产品技术方案： 根据模板 ./references/tech_design.md 生成技术方案。架构图、框架图、流程图、ER 图等等均使用 $diagram-design 作图。
