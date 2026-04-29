# {{REPORT_TITLE}}

## 1. 分析范围

- 仓库：`{{REPO_NAME}}`
- 路径范围：`{{ANALYSIS_PATH}}`
- 时间窗口：`{{DATE_RANGE}}`
- 生成时间：`{{GENERATED_AT}}`

{{OVERVIEW_BULLETS}}

## 2. 核心指标

{{OVERVIEW_STATS_TABLE}}

## 3. 热点与风险

### 3.1 高频变更文件

{{HOTSPOT_TABLE}}

### 3.2 综合风险文件

{{RISK_TABLE}}

### 3.3 活跃目录

{{DIRECTORY_TABLE}}

## 4. 协作与耦合

### 4.1 作者分布

{{AUTHOR_TABLE}}

### 4.2 单点拥有风险

{{OWNERSHIP_TABLE}}

### 4.3 时间耦合

{{COUPLING_TABLE}}

## 5. 陈旧度与知识流失

### 5.1 陈旧代码

{{STALENESS_TABLE}}

### 5.2 知识流失

{{KNOWLEDGE_LOSS_TABLE}}

## 6. AI 辅助开发观察

{{AI_ANALYSIS_SECTION}}

## 7. 建议动作

{{PRIORITY_ACTIONS}}

## 8. 备注

{{METHOD_NOTES}}

待人工补充：

- 结合业务事故、线上告警、返工记录，对高风险文件做二次排序。
- 识别“高 churn 但低业务价值”的历史包袱，避免误把噪声当成核心问题。
