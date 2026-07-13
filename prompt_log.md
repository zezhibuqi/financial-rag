# Prompt 日志 (prompt_log.md)

> **项目**: financial-rag
> 
> **说明**: 本日志记录项目开发全周期的 Prompt 交互。记录了从环境配置、数据灌库、后端逻辑调试（特别是RAG优化）、前端交互实现到最终部署的全过程。已脱敏API密钥及因网络中断导致的冗余对话。

---

## 1. 项目初始化与配置

### 1.1 初始化 Matt Pocock Skills

- **Prompt**: "`setup-matt-pocock-skills`"
    
- **功能/文件**: `AGENTS.md`
    
- **AI 返回要点**:
    
    - 检测项目环境，确认存在 `.git`文件夹。
        
    - 引导用户选择 Issue Tracker（用户选择稍后配置 GitHub）。
        
    - 确认使用默认的 Triage labels 和 Single-context 架构。
        
    - 在 `AGENTS.md`中写入 Agent skills 配置块。
        
    

### 1.2 环境依赖安装与故障排查

- **Prompt**: "检查项目设计文档和项目实施文档，看一下NumPy版本能不能换成2.0.0+，因为当前python版本是3.8"
    
- **功能/文件**: `requirements.txt`
    
- **AI 返回要点**:
    
    - 指出 NumPy 2.0+ 不支持 Python 3.8。
        
    - 建议锁定 `numpy==1.26.4`。
        
    
- **Prompt**: "执行pip install pdfplumber... numpy==1.26.4遇到如下问题... ERROR: NumPy requires GCC >= 8.4"
    
- **功能/文件**: 本地编译环境
    
- **AI 返回要点**:
    
    - 诊断出本地 MinGW-w64 的 GCC 版本为 8.1.0，不满足 NumPy 编译要求。
        
    - 建议下载预编译的 Wheel 文件或调整环境。
        
    
- **Prompt**: "我在进行项目实施文档中的embedding预热... huggingface_hub.errors.LocalEntryNotFoundError... ConnectionResetError"
    
- **功能/文件**: 模型缓存
    
- **AI 返回要点**:
    
    - 诊断网络连接问题（代理/防火墙导致 HuggingFace 连接重置）。
        
    - 建议配置代理环境变量（`HTTP_PROXY`/`HTTPS_PROXY`）或使用国内镜像。
        
    - 指导用户利用已下载的本地缓存加载模型：`SentenceTransformer('BAAI/bge-large-zh-v1.5')`不传路径。
        
    

### 1.3 服务启动与Git配置

- **Prompt**: "重启电脑后该怎么启动"
    
- **功能/文件**: 开发流程
    
- **AI 返回要点**:
    
    - 提供启动脚本：激活虚拟环境、启动后端 Flask 服务、启动前端 Next.js 开发服务器。
        
    
- **Prompt**: "我现在无法把代码提交到github仓库，trae内显示提交完成，点击在github中查看显示404... Git: fatal: unable to access... Recv failure: Connection was reset"
    
- **功能/文件**: Git / Network
    
- **AI 返回要点**:
    
    - 确认远程仓库 `https://github.com/zezhibuqi/financial-rag`存在。
        
    - 诊断网络重置问题，建议检查代理设置或执行 `git push -u origin main`。
        
    - 确认 `gh`CLI 在 CMD 中可用，但在 TRAE 内置终端可能存在环境变量隔离问题。
        
    

---

## 2. 核心逻辑确认 (Grill-with-docs)

### 2.1 项目参数对齐

- **Prompt**: "`grill-with-docs`... 我按照实施文档已完成到0.4 预热 Embedding 模型... 现在需要你和我确认这个项目的实现细节"
    
- **功能/文件**: `项目设计文档.md`, `项目实施文档.md`
    
- **AI 返回要点**:
    
    - **数据源**: 确认仅保留茅台和宁德时代两家公司，各3份年报（23,24,25年）。
        
    - **切片策略**: 确认按字符数 512 切分（修正文档中“512 tokens”的不精确表述）。
        
    - **前端筛选**: 确认采用方案A（两个下拉框：公司、年份，“不限”为默认选项）。
        
    - **模型选型**: 确认 LLM 使用 Deepseek，Embedding 使用本地缓存的 BGE 模型。
        
    - **灌库策略**: 确认 6 个 PDF 平铺一次性跑，并采纳“灌入前先删除旧数据”的幂等性方案。
        
    - **交互模式**: 确认采用方案A（一次性返回，非流式）。
        
    - **存储**: 确认 Supabase Storage Bucket 名为 `pdfs`。
        
    

---

## 3. 后端开发：RAG 管线优化

### 3.1 召回失败修复（利润查询）

- **Prompt**: "我询问‘2025年茅台利润多少’,底下资料显示中有对应资料，但回答依旧是未在资料中找到"
    
- **功能/文件**: `backend/app.py`(`/api/chat`)
    
- **AI 返回要点**:
    
    - 分析原因为 Embedding 语义偏移及 Prompt 约束过严。
        
    - 修改 Prompt 指令：改为“理解片段并回答问题，如果按理解片段中没有相关内容，再返回未在资料中找到”。
        
    - 实施关键词兜底逻辑，确保“利润”相关片段能被召回。
        
    

### 3.2 跨公司对比修复

- **Prompt**: "我发现‘宁德时代和茅台2024年谁的利润更高’，无法正确回答"
    
- **功能/文件**: `backend/app.py`
    
- **AI 返回要点**:
    
    - 分析原因为未区分公司实体，导致上下文混淆。
        
    - 修改逻辑：提取问题中的公司名和年份，分别进行关键词检索，确保两家公司的数据都能进入 Context。
        
    

### 3.3 Rerank 策略重构（关键优化）

- **Prompt**: "`grill-with-docs`我注意到我们召回的片段并没有进行重排，我觉得可以rerank后再发送给llm，你觉得可行吗"
    
- **功能/文件**: `backend/app.py`(新增 `rerank_chunks`函数)
    
- **AI 返回要点**:
    
    - 评估方案：否决“仅向量结果Rerank+关键词直通LLM”（方案A），采纳“全量混合Rerank”（方案B）。
        
    - 集成 SiliconFlow API (`BAAI/bge-reranker-v2-m3`)。
        
    - **关键修正**: 针对财务表格数据，发现 Reranker 对长表格评分偏低。最终调整为：**向量结果 Rerank 取 Top-4 + 关键词结果每公司保底 2 条**，混合输入 LLM，兼顾语义准确度与关键数据完整性。
        
    - 修复 `FINANCE_KW_MAP`中关键词重叠导致的笛卡尔积爆炸问题（拍平列表+设置 `MAX_KW_CHUNKS=6`）。
        
    

### 3.4 数据完整性验证

- **Prompt**: "我测试‘宁德时代2023年到2025年的经营活动现金流净额分别是多少’... 下方的参考来源只有4个片段"
    
- **功能/文件**: `backend/app.py`
    
- **AI 返回要点**:
    
    - 分析原因为关键词补充逻辑限制了返回条数。
        
    - 调整 `top_n`参数及关键词兜底逻辑，确保跨年查询能召回足够多的片段。
        
    
- **Prompt**: "询问‘宁德时代和贵州茅台2023年...营业收入...’，片段只有6个...未找到宁德时代"
    
- **功能/文件**: `backend/app.py`
    
- **AI 返回要点**:
    
    - 确认为召回逻辑中公司过滤条件过于严格或数据确实缺失。
        
    - 优化 SQL 查询逻辑，放宽限制以确保两家公司的数据都能被扫描到。
        
    

---

## 4. 前端开发

### 4.1 Markdown 渲染支持

- **Prompt**: "修改下前端界面的回答显示部分，回答的内容均为markdown格式，但显示却按普通文字显示，并未按markdown渲染"
    
- **功能/文件**: `frontend/pages/index.tsx`
    
- **AI 返回要点**:
    
    - 引入 `react-markdown`库。
        
    - 替换原有的 Ant Design 文本组件，支持粗体、表格、列表等格式。
        
    

### 4.2 参考来源交互优化

- **Prompt**: "我注意到回答区域下方的参考来源区域...我希望这些片段能点击展开完整显示，默认没点击时还是和现在一样的粗略显示，可行吗"
    
- **功能/文件**: `frontend/pages/index.tsx`
    
- **AI 返回要点**:
    
    - 后端接口新增返回 `content`(完整文本) 字段。
        
    - 前端实现折叠逻辑：仅当文本长度大于 200 字符时显示“展开”按钮，点击后切换显示完整内容。
        
    

### 4.3 筛选框加载失败修复

- **Prompt**: "浏览器打开前端后显示加载筛选选项失败...请求失败"
    
- **功能/文件**: `frontend/pages/index.tsx`, `backend/app.py`(`/api/docs`)
    
- **AI 返回要点**:
    
    - 修复前端 API 调用路径在 Vercel 生产环境下的指向问题。
        
    - 确保 `/api/docs`接口能正确返回扁平结构的公司和年份列表。
        
    

---

## 5. 部署与运维 (Vercel)

### 5.1 项目部署

- **Prompt**: "好，现在可以进入第四阶段将前端部署至 Vercel，后端部署至 Vercel Serverless"
    
- **功能/文件**: `backend/api/index.py`, `vercel.json`
    
- **AI 返回要点**:
    
    - 配置 Vercel Serverless Functions，适配 Flask 应用。
        
    - 解决依赖冲突：锁定 `supabase`, `openai`, `httpx`版本。
        
    - 修复环境变量注入问题：在代码中添加硬编码 Fallback URL，应对浏览器缓存导致的环境变量未更新。
        
    

### 5.2 密钥轮换与安全

- **Prompt**: "Deepseek的api key：sk-xxx，硅基流动的api key：sk-yyy... 你帮我更换一下。项目已经部署到vercel上，你同时更新一下"
    
- **功能/文件**: Vercel Environment Variables
    
- **AI 返回要点**:
    
    - 指导用户在 Vercel 控制台更新环境变量（DeepSeek Key, SiliconFlow Key）。
        
    - 触发重新部署以使环境变量生效。
        
    - 清理 Git 历史中的 `.env`文件，确保密钥未泄露。
        
    

### 5.3 代码同步与清理

- **Prompt**: "阅读整个项目，判断哪些该上传github及哪些不该上传...操作前先经我确认"
    
- **功能/文件**: `.gitignore`
    
- **AI 返回要点**:
    
    - 确认 `.env`, `__pycache__/`, `backend/pdfs/`等不应上传。
        
    - 生成并提交 `.gitignore`文件。
        
    - 协助修改提交信息为中文（如“更新RAG管线逻辑”），并推送至 GitHub。
        
    

---

## 6. 文档与复盘

### 6.1 API 文档生成

- **Prompt**: "写一份简短的 API 接口文档...单独抽出来整理成api.md"
    
- **功能/文件**: `api.md`
    
- **AI 返回要点**:
    
    - 从项目设计文档中提取 `/api/docs`和 `/api/chat`的定义。
        
    - 整理 Method、路径、请求参数（JSON Body）及响应示例。
        
    

### 6.2 项目文档更新

- **Prompt**: "根据目前的项目，更新项目设计文档和项目实施文档"
    
- **功能/文件**: `项目设计文档.md`, `项目实施文档.md`
    
- **AI 返回要点**:
    
    - 同步最新的 RAG 管线图（含 Rerank 节点）。
        
    - 更新 Golden Set 测试用例（移除招商银行，聚焦茅台与宁德时代）。
        
    - 修正切片单位（字符 vs tokens）等技术细节。
        
    

### 6.3 汇报材料生成

- **Prompt**: "等会我要向指导老师介绍这个项目，你生成一个markdown文档供我参考"
    
- **功能/文件**: `项目介绍.md`
    
- **AI 返回要点**:
    
    - 梳理项目亮点：混合检索（向量+关键词）、Rerank 重排、前端 Markdown 渲染。
        
    - 编排演示脚本：单指标查询 -> 跨公司对比 -> 跨年数据分析。
        
    - 绘制技术架构图。
        
    

---

## 附录：核心代码片段示例

### Rerank 集成逻辑 (最终版)

```
# 合并去重（向量 + 关键词，按 id）
all_chunks = []
seen = set()
for r in result.data:
    if r['id'] not in seen:
        seen.add(r['id'])
        all_chunks.append(r)

try:
    # 全量送入 Reranker
    ranked = rerank_chunks(question, all_chunks, top_n=6)
except Exception:
    # Fallback 逻辑
    ranked = sorted(all_chunks, key=lambda x: x.get('similarity', 0), reverse=True)[:6]
    for c in ranked:
        c['rerank_score'] = c.get('similarity', 0)
```

### 关键词映射表 (FINANCE_KW_MAP)

```
FINANCE_KW_MAP = {
    "利润": ["净利润", "利润总额", "归母净利润"],
    "营收": ["营业收入", "营业总收入"],
    "现金流": ["经营活动产生的现金流量净额", "经营活动现金流"],
    "毛利率": ["毛利率", "综合毛利率"],
    "分红": ["利润分配预案", "每10股派发现金红利", "分红方案"]
}
```

---

_日志结束_

---