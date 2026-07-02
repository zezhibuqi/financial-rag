# API 接口文档

Base URL: `http://localhost:5000`（开发环境）/ 部署后为 Vercel 域名

---

## POST /api/chat

RAG 问答接口。

**Method**: `POST`

**Content-Type**: `application/json`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 用户问题 |
| `company` | string | 否 | 公司简称（`茅台` / `宁德时代`），不传则自动从问题提取 |
| `year` | int | 否 | 财务年份（`2023` / `2024` / `2025`），不传则自动从问题提取 |

**请求示例**:

```json
{
  "question": "茅台2023年毛利率是多少？",
  "company": "茅台",
  "year": 2023
}
```

**成功响应**:

```json
{
  "answer": "根据财报片段，贵州茅台2023年酒类业务的毛利率为 **92.11%**...",
  "sources": [
    {
      "doc_name": "贵州茅台2023年度报告.pdf",
      "page": 14,
      "content": "完整chunk内容...",
      "snippet": "前200字符摘要...",
      "similarity": 0.9924,
      "source": "vector"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `similarity` | Rerank 后的 relevance_score（0~1） |
| `source` | `vector`（向量检索）/ `keyword`（关键词补充） |
| `content` | Chunk 完整原文 |
| `snippet` | 前 200 字符摘要 |

**错误响应**:

```json
{"error": "问题不能为空"}
```

---

## POST /api/upload

上传 PDF 年报至 Supabase Storage（不触发解析）。

**Method**: `POST`

**Content-Type**: `multipart/form-data`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | PDF 文件 |

**成功响应**:

```json
{
  "msg": "文件已上传，管理员将在本地完成解析入库",
  "file_id": "贵州茅台2023年度报告.pdf"
}
```

**错误响应**:

```json
{"error": "请选择要上传的文件"}
```

---

## GET /api/docs

获取已入库年报列表及筛选选项。

**Method**: `GET`

**请求参数**: 无

**响应示例**:

```json
{
  "companies": ["宁德时代", "茅台"],
  "years": [2023, 2024, 2025],
  "docs": [
    {
      "doc_name": "贵州茅台2023年度报告.pdf",
      "company": "茅台",
      "year": 2023,
      "chunk_count": 685,
      "uploaded_at": "2026-07-01T13:10:00Z"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `companies` | distinct 公司简称，用于前端下拉框 |
| `years` | distinct 年份，用于前端下拉框 |
| `docs` | 按 `doc_name` 去重聚合的年报列表 |

---

## 错误码

所有接口业务错误返回 HTTP 200，通过 `error` 字段区分：

| 场景 | 错误信息 |
|------|---------|
| question 为空 | "问题不能为空" |
| 未上传文件 | "请选择要上传的文件" |
| 同名文件已存在 | "同名文件已存在" |
| Embedding 失败 | "Embedding服务不可用，请稍后重试" |
| 数据库失败 | "数据库查询失败，请稍后重试" |
| LLM 失败 | "AI服务暂时不可用，请稍后重试" |
