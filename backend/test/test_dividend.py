"""测试分红查询"""
import requests, time

t0 = time.time()
r = requests.post('http://localhost:5000/api/chat', json={
    'question': '茅台2023年到2025年的分红方案分别是？'
})
d = r.json()
print(f"Time: {time.time()-t0:.1f}s")
print(f"Answer:\n{d['answer'][:600]}")
print(f"\nSources: {len(d['sources'])}")
for s in d['sources']:
    print(f"  [{s['similarity']:.4f}] {s['source']} {s['doc_name']} p{s['page']}")
