"""
Flask 后端 —— 财报智能问答系统 RAG 核心链路

接口：
    POST /api/chat   → RAG 问答
    POST /api/upload → PDF 上传（仅存 Supabase Storage）
    GET  /api/docs   → 已入库年报列表 + 公司/年份筛选选项
"""

import os
import sys
import re as _re
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# ---------------------------------------------------------------------------
# 加载环境变量（本地开发用 .env，Vercel 上走系统环境变量）
# ---------------------------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-v4-flash')
EMBEDDING_API_KEY = os.getenv('EMBEDDING_API_KEY')
EMBEDDING_API_BASE = os.getenv('EMBEDDING_API_BASE')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-large-zh-v1.5')

# 验证必要环境变量
for _key, _name in [
    (SUPABASE_URL, 'SUPABASE_URL'),
    (SUPABASE_ANON_KEY, 'SUPABASE_ANON_KEY'),
    (LLM_API_KEY, 'LLM_API_KEY'),
    (LLM_API_BASE, 'LLM_API_BASE'),
    (EMBEDDING_API_KEY, 'EMBEDDING_API_KEY'),
    (EMBEDDING_API_BASE, 'EMBEDDING_API_BASE'),
]:
    if not _key:
        raise RuntimeError(f'缺少环境变量: {_name}')

# ---------------------------------------------------------------------------
# 初始化客户端
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

llm_client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_API_BASE,
)

embedding_client = OpenAI(
    api_key=EMBEDDING_API_KEY,
    base_url=EMBEDDING_API_BASE,
)

RERANK_MODEL = 'BAAI/bge-reranker-v2-m3'
RERANK_URL = f'{EMBEDDING_API_BASE}/rerank'


def rerank_chunks(query: str, chunks: list, top_n: int = 6) -> list:
    """调用 SiliconFlow Rerank API 对 chunks 重排，返回 top_n 条（带 rerank_score）。"""
    if not chunks:
        return []
    if len(chunks) == 1:
        chunks[0]['rerank_score'] = chunks[0].get('similarity', 0)
        return chunks

    documents = [c['content'] for c in chunks]
    resp = requests.post(
        RERANK_URL,
        json={
            "model": RERANK_MODEL,
            "query": query,
            "documents": documents,
            "return_documents": False,
            "top_n": min(top_n, len(chunks)),
        },
        headers={
            "Authorization": f"Bearer {EMBEDDING_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get('results', [])

    ranked = []
    for r in results:
        idx = r['index']
        chunk = chunks[idx].copy()
        chunk['rerank_score'] = r['relevance_score']
        ranked.append(chunk)

    return ranked[:top_n] if top_n > 0 else ranked


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    company = data.get('company') or None
    year = data.get('year') or None

    # ---- 验证 ----
    if not question:
        return jsonify({"error": "问题不能为空"})

    # ---- 1. Embedding ----
    try:
        resp = embedding_client.embeddings.create(
            input=question,
            model=EMBEDDING_MODEL,
        )
        question_emb = resp.data[0].embedding
    except Exception:
        return jsonify({"error": "Embedding服务不可用，请稍后重试"})

    # ---- 2. 检索 ----
    try:
        result = supabase.rpc('match_chunks', {
            'query_embedding': question_emb,
            'match_count': 10,
            'filter_company': company or None,
            'filter_year': year or None,
        }).execute()
    except Exception:
        return jsonify({"error": "数据库查询失败，请稍后重试"})

    if not result.data:
        return jsonify({
            "answer": "未找到相关财报数据，请确认已灌库。",
            "sources": [],
        })

    # 标记向量检索的来源
    for r in result.data:
        r['source'] = 'vector'

    # ---- 2b. 关键词补充：常见财务指标无条件补充分词检索 ----
    # 映射：用户提问词 → 数据库中实际出现的财务术语
    FINANCE_KW_MAP = {
        '利润': ['净利润', '利润总额'],
        '净利润': ['净利润', '利润总额'],
        '现金流': ['经营活动产生的现金流量净额', '现金流量'],
        '毛利率': ['毛利率'],
        '营收': ['营业收入'],
        '收入': ['营业收入'],
        '总资产': ['总资产', '资产总计'],
        '净资产': ['归属于上市公司股东的净资产', '净资产'],
        '负债': ['负债合计', '总负债'],
        '每股收益': ['基本每股收益', '每股收益'],
        '分红': ['现金分红', '派发现金红利', '利润分配'],
    }

    triggered_kws = [v for k, v in FINANCE_KW_MAP.items() if k in question]
    if triggered_kws:
        try:
            # 1. 拍平 + 去重触发词
            triggered_kws_flat = list({kw for v in triggered_kws for kw in v})

            keyword_years = []
            if year:
                keyword_years = [year]
            else:
                year_matches = _re.findall(r'(\d{4})\s*年', question)
                keyword_years = [int(y) for y in year_matches] if year_matches else [None]

            companies_to_search = [company] if company else []
            if not companies_to_search:
                if '茅台' in question or '贵州茅台' in question:
                    companies_to_search = ['茅台']
                if '宁德' in question:
                    companies_to_search.append('宁德时代')
                if not companies_to_search:
                    companies_to_search = ['茅台', '宁德时代']

            existing_ids = {r.get('id') for r in result.data}
            MAX_KW_CHUNKS_PER_COMPANY = 4
            kw_count = {}
            for comp in companies_to_search:
                kw_count[comp] = 0

            for db_kw in triggered_kws_flat:
                for comp in companies_to_search:
                    if kw_count[comp] >= MAX_KW_CHUNKS_PER_COMPANY:
                        continue
                    for kw_year in keyword_years:
                        if kw_count[comp] >= MAX_KW_CHUNKS_PER_COMPANY:
                            break
                        query = supabase.table('chunks').select('*').eq('company', comp)
                        if kw_year:
                            query = query.eq('year', kw_year)
                        kw_chunks = query.like('content', f'%{db_kw}%').limit(2).execute()
                        for c in (kw_chunks.data or []):
                            if c.get('id') not in existing_ids:
                                existing_ids.add(c['id'])
                                c['source'] = 'keyword'
                                c['similarity'] = 0
                                result.data.append(c)
                                kw_count[comp] += 1
                                if kw_count[comp] >= MAX_KW_CHUNKS_PER_COMPANY:
                                    break
        except Exception:
            pass

    # ---- 3. Rerank（全量 → 向量 top-4 + 关键词 best-2 混合精排） ----
    all_chunks = []
    seen = set()
    for r in result.data:
        if r['id'] not in seen:
            seen.add(r['id'])
            all_chunks.append(r)

    try:
        all_ranked = rerank_chunks(question, all_chunks, top_n=len(all_chunks) + 50)
    except Exception:
        all_ranked = sorted(all_chunks, key=lambda x: x.get('similarity', 0), reverse=True)
        for c in all_ranked:
            c['rerank_score'] = c.get('similarity', 0)

    # 分别取：向量 top-4 + 关键词每公司 best-2（按真实 rerank_score，保证两家公司数据覆盖）
    vector_ranked = [c for c in all_ranked if c.get('source') == 'vector'][:4]
    ranked = list(vector_ranked)

    # 关键词 Chunk：每家已出现的公司至少保留 2 条
    company_kw_count = {}
    for c in all_ranked:
        if c.get('source') != 'keyword':
            continue
        comp = c.get('company', '__unknown__')
        if company_kw_count.get(comp, 0) >= 2:
            continue
        company_kw_count[comp] = company_kw_count.get(comp, 0) + 1
        ranked.append(c)
        if len(ranked) >= 8:
            break

    # ---- 4. 组装 Prompt ----
    chunks_text = ''
    for r in ranked:
        chunks_text += (
            f'\n--- [{r.get("company", "")} {r.get("year", "")}年报 第{r["page"]}页] ---\n'
            f'{r["content"]}\n'
        )
    prompt = (
    '你是一个专业的财报分析助手。你的任务是基于提供的财报片段，尽可能准确地回答用户问题。\n\n'
    '回答要求：\n'
    '1. 优先从片段中提取具体数字和原文表述来回答\n'
    '2. 如果片段中有相关数据但不完全匹配问题，请给出最接近的数据并说明来源\n'
    '3. 只有当片段中完全没有与问题相关的任何信息时，才回答"未在资料中找到相关信息"\n'
    '4. 回答中引用具体数字时，注明出自哪个报表项目\n\n'
    '---财报片段---\n'
    f'{chunks_text}\n'
    '---片段结束---\n\n'
    f'问题：{question}\n\n'
    '回答（基于以上片段）：'
    )

    # ---- 5. 生成回答 ----
    try:
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = resp.choices[0].message.content
    except Exception:
        return jsonify({"error": "AI服务暂时不可用，请稍后重试"})

    # ---- 6. 组装 sources ----
    sources = [
        {
            "doc_name": r['doc_name'],
            "page": r['page'],
            "content": r['content'],
            "snippet": r['content'][:200],
            "similarity": round(r.get('rerank_score', r.get('similarity', 0)), 4),
            "source": r.get('source', 'vector'),
        }
        for r in ranked
    ]

    return jsonify({"answer": answer, "sources": sources})


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------
@app.route('/api/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "请选择要上传的文件"})

    try:
        supabase.storage.from_('pdfs').upload(
            file.filename,
            file.read(),
            {"content-type": "application/pdf"},
        )
    except Exception as e:
        err = str(e)
        if 'already exists' in err.lower():
            return jsonify({"error": "同名文件已存在"})
        return jsonify({"error": f"上传失败：{err}"})

    return jsonify({
        "msg": "文件已上传，管理员将在本地完成解析入库",
        "file_id": file.filename,
    })


# ---------------------------------------------------------------------------
# GET /api/docs
# ---------------------------------------------------------------------------
@app.route('/api/docs', methods=['GET'])
def docs():
    try:
        count_resp = supabase.table('chunks').select('*', count='exact').limit(1).execute()
        total = count_resp.count

        # Supabase 每次最多返回 1000 条，需要分页
        PAGE = 1000
        all_data = []
        for offset in range(0, total, PAGE):
            end = min(offset + PAGE - 1, total - 1)
            page = supabase.table('chunks').select('doc_name,company,year,uploaded_at') \
                .range(offset, end).execute()
            all_data.extend(page.data)
    except Exception:
        return jsonify({"error": "数据库查询失败"})

    data = all_data
    if not data:
        return jsonify({"companies": [], "years": [], "docs": []})

    # distinct company / year
    companies = sorted(set(r['company'] for r in data))
    years = sorted(set(r['year'] for r in data))

    # 按 doc_name 聚合
    docs_map = {}
    for r in data:
        key = r['doc_name']
        if key not in docs_map:
            docs_map[key] = {
                "doc_name": r['doc_name'],
                "company": r['company'],
                "year": r['year'],
                "chunk_count": 0,
                "uploaded_at": r['uploaded_at'],
            }
        docs_map[key]['chunk_count'] += 1

    return jsonify({
        "companies": companies,
        "years": years,
        "docs": list(docs_map.values()),
    })


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
