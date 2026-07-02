# 财报智能问答系统（RAG）

基于 RAG（检索增强生成）技术的财报智能问答系统，支持贵州茅台和宁德时代 2023-2025 年度报告的自然语言问答。

> 线上地址：https://frontend-sigma-nine-90.vercel.app
> 国内得挂VPN

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + Ant Design + react-markdown |
| 后端 | Python Flask（本地）/ Vercel Serverless（线上） |
| 数据库 | Supabase PostgreSQL + pgvector |
| Embedding | BAAI/bge-large-zh-v1.5（本地 GPU / SiliconFlow API） |
| Reranker | BAAI/bge-reranker-v2-m3（SiliconFlow API） |
| LLM | DeepSeek API |
| PDF 解析 | pdfplumber |
| 部署 | Vercel |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- CUDA GPU（可选，用于本地 Embedding）

### 1. 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install flask flask-cors supabase openai python-dotenv requests
python app.py  # → http://localhost:5000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev  # → http://localhost:3000
```

### 3. 离线数据灌库

```bash
# 将 PDF 放入 backend/pdfs/ 目录，然后运行：
python backend/ingest.py
```

## RAG 管线

```
Query → Embedding → 向量检索(k=10) + 关键词补充
       → 去重 → Rerank → 向量top-4 + 关键词per-company best-2
       → Prompt → DeepSeek → {answer, sources}
```

## API 接口

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/chat` | RAG 问答 |
| POST | `/api/upload` | PDF 上传 |
| GET | `/api/docs` | 已入库年报列表 + 筛选选项 |

详见 [api.md](./api.md)

## 项目文档

- [项目设计文档](./项目设计文档.md)
- [项目实施文档](./项目实施文档.md)
- [API 接口文档](./api.md)

## 测试

```bash
python backend/test/test_chat_single.py    # 单公司查询
python backend/test/test_chat_cross.py     # 跨公司比较
python backend/test/test_cashflow.py       # 现金流查询
python backend/test/test_dividend.py       # 分红查询
python backend/test/test_revenue.py        # 营收对比
python backend/test/golden_set.py          # Golden Set 验收
```
