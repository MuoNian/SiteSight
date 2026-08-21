# 鹭见 SiteSight · 设计系统

> 由 built world 记录（impeccable new-work，seed 2a28bd17，降级滚动）。方向：**场地剖面仪**——把网页读成一件读取地层的仪器。

## 世界（World）

暖纸底的工作台 + 墨色仪器面板：页面像一张放在图板上的场地剖面记录，等高线、地层带、高程标尺是它自带的纹理。琥珀色（取样琥珀）只在动作与选中态出现；数据全部用等宽数字，像仪器读数。

## 调色板（Tokens）

```text
--paper:#f4f1e9      暖纸底
--surface:#fffdf8    面板表面
--ink:#212b3a        墨色正文
--ink-2:#46525f      次级文字
--ink-3:#5c6a7a      提示/占位
--line:#e2dccd / --line-2:#d3cab8   图纸线
--accent:#b45f1f     琥珀（动作/选中）
--accent-deep:#96501a
--accent-soft:#f6e9dc
--ok:#2f7d5b / --err:#b4432e / --info:#3b6ea5 / --focus:#1f6fae
--panel:#1c2735      仪器面板（深墨）
--panel-line:#37465a
```

策略：Restrained（中性 + 单强调色），唯一彩色区域是深墨仪器面板与琥珀动作色。

## 字体（Type）

- 单一无衬线族（系统栈 + 中文雅黑/苹方），无衬线用于全部界面
- 等宽族（Consolas / JetBrains Mono / SF Mono）只用于数据、编号、读数、日志
- 固定 rem 阶梯：h1 2.5rem → h2 1.5rem → h3 1.06-1.08rem → 正文 .93rem
- 标题字距 -0.02em；正文行高 1.6

## 组件（Components）

- 面板：圆角 14px、单一软阴影、无描边；一个容器一层阴影，不套嵌卡片
- 按钮：`btn-accent`（琥珀）/ `btn-primary`（墨）/ `btn-ghost`（线框）；统一 10px 圆角、600 字重；hover / active / disabled / focus-visible 全态
- 输入：1.5px 图纸线，focus 变信息蓝 + 3px 光晕
- 流程条：地层带（垂直岩芯剖面样式），编号圆点 + 连续纵线
- 仪器面板：深墨底、等宽读数、等高线 SVG 叠层、高程标尺；扫描线为唯一动效瞬间（1.8s 一次）
- 表格/日志/报告块：等宽数字列、深色日志盒、暖色报告块

## 动效（Motion）

- 状态动效 150-250ms：按钮 hover/active、输入 focus、进度条 transform scaleX
- 唯一作者时刻：仪器面板进场扫描线（cubic-bezier(.22,.61,.36,1)）
- 尊重 prefers-reduced-motion

## 布局（Layout）

- 页面 1140px 容器；hero 为两栏（主张 1.04fr / 仪器 0.96fr）
- 工作台 940px 单列，面板纵向堆叠（任务路径单一）
- 断点：960px hero 折单栏；640px 读数四格折两格、路径输入折列

## 状态与可达性

- 正文/占位对比度 ≥4.5:1；focus-visible 可见；选区与滚动条从调色板定制
- 空态/错误态有中文说明与恢复路径（如云端无建模引擎时的横幅提示）

## 评审记录（Degraded）

- 检测器（detect.mjs）以降级模式运行（无 HTML 解析器），发现并修复：进度条 width 动画 → transform scaleX；扫描线彩色光晕移除
- 本环境无截图渲染链路，未做桌面/移动像素级对照；方向契约已写入 index.html body 注释，DESIGN.md 已记录
