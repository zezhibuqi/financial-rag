"""
Flask 后端 —— 财报智能问答系统 RAG 核心链路

接口：
    POST /api/chat   → RAG 问答
    POST /api/upload → PDF 上传（仅存 Supabase Storage）
    GET  /api/docs   → 已入库年报列表 + 公司/年份筛选选项
"""

import os
import sys

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# ---------------------------------------------------------------------------
# 加载环境变量
# ---------------------------------------------------------------------------
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-v4-flash')
EMBEDDING_API_KEY = os.getenv('EMBEDDING_API_KEY')
EMBEDDING_API_BASE = os.getenv('EMBEDDING_API_BASE')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-large-zh-v1.5')

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
            'match_count': 4,
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

    # ---- 3. 组装 Prompt ----
    chunks_text = '\n---\n'.join(r['content'] for r in result.data)
    prompt = (
        '你是一个财报分析助手。请根据以下财报片段回答问题，'
        '若片段中无明确答案，请直接说"未在资料中找到"。\n'
        '---片段开始---\n'
        f'{chunks_text}\n'
        '---片段结束---\n'
        f'问题：{question}\n'
        '回答（仅基于片段，不要外延）：'
    )

    # ---- 4. 生成回答 ----
    try:
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = resp.choices[0].message.content
    except Exception:
        return jsonify({"error": "AI服务暂时不可用，请稍后重试"})

    # ---- 5. 组装 sources ----
    sources = [
        {
            "doc_name": r['doc_name'],
            "page": r['page'],
            "snippet": r['content'][:200],
            "similarity": round(r['similarity'], 4),
        }
        for r in result.data
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
