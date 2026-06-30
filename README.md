# 财报智能问答系统（RAG）

基于 RAG（检索增强生成）技术的财报智能问答系统，支持上传 PDF 财报文档，通过自然语言提问获取带引用的智能回答。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + Ant Design |
| 后端 | Python Flask |
| 数据库 | Supabase PostgreSQL + pgvector |
| Embedding | BAAI/bge-large-zh-v1.5（本地 GPU / SiliconFlow API） |
| LLM | 混元 / DeepSeek API |
| PDF 解析 | pdfplumber |

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- CUDA GPU（可选，用于本地 Embedding）

### 2. 后端部署

```bash
# 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate  # Windows
pip install flask flask-cors supabase pdfplumber sentence-transformers langchain-text-splitters openai python-dotenv

# 配置环境变量（复制 .env.example 并填写密钥）
cp .env.example .env
```

### 3. 前端部署

```bash
cd frontend
npm install
npm run dev
```

### 4. 离线数据灌库

```bash
python ingest.py --pdf path/to/report.pdf
```

## 系统架构

```
前端（Next.js） → 后端（Flask） → Supabase（pgvector 检索） → LLM（生成回答）
                      ↑
                离线预处理（PDF解析 → 切片 → Embedding → 入库）
```

## 功能特性

- PDF 财报文档上传与管理
- 自然语言智能问答
- 回答附带引用来源（公司、年份、页码）
- 支持按公司、年份筛选
- 本地 GPU 加速 Embedding（可选）

## 文档

- [项目设计文档](./项目设计文档.md) — 架构设计、技术选型、数据库设计
- [项目实施文档](./项目实施文档.md) — 分阶段开发指南