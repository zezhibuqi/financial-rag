"""Reranker 评分分析脚本 —— 对比向量 Chunk 与关键词 Chunk 在 Reranker 下的得分"""
import os, json
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI
import requests as req

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
emb_client = OpenAI(api_key=os.getenv('EMBEDDING_API_KEY'), base_url=os.getenv('EMBEDDING_API_BASE'))

q = '宁德时代和茅台2024年谁的利润更高'

# Vector search
resp = emb_client.embeddings.create(input=q, model='BAAI/bge-large-zh-v1.5')
r = supabase.rpc('match_chunks', {
    'query_embedding': resp.data[0].embedding, 'match_count': 10,
    'filter_company': None, 'filter_year': None,
}).execute()

# Keyword search
keyword_chunks = []
for kw in ['净利润', '利润总额']:
    for comp in ['茅台', '宁德时代']:
        kc = supabase.table('chunks').select('*').eq('company', comp).eq('year', 2024).like('content', f'%{kw}%').limit(2).execute()
        keyword_chunks.extend(kc.data or [])

print(f"Vector: {len(r.data)}, Keyword: {len(keyword_chunks)}")

# Merge & dedup
existing_ids = {c.get('id') for c in r.data}
for c in keyword_chunks:
    if c.get('id') not in existing_ids:
        existing_ids.add(c['id'])
        r.data.append(c)

print(f"Merged: {len(r.data)} (first 10 = vector)\n")

# Rerank
documents = [c['content'] for c in r.data]
rerank_resp = req.post(
    'https://api.siliconflow.cn/v1/rerank',
    json={"model": "BAAI/bge-reranker-v2-m3", "query": q, "documents": documents, "return_documents": False},
    headers={"Authorization": f"Bearer {os.getenv('EMBEDDING_API_KEY')}", "Content-Type": "application/json"},
    timeout=15,
)
results = rerank_resp.json().get('results', [])

print("Rerank results (sorted by relevance):")
for rr in sorted(results, key=lambda x: x['relevance_score'], reverse=True):
    idx = rr['index']
    c = r.data[idx]
    is_kw = idx >= 10
    print(f"  [{rr['relevance_score']:.4f}] {'KEYWORD' if is_kw else 'VECTOR'} | {c.get('doc_name','?')} p{c.get('page','?')}")
    print(f"    {c.get('content','')[:120].replace(chr(10), ' ')}")
    print()
