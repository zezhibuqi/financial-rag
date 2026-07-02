"""测试单公司查询 + Rerank 效果"""
import requests, time

t0 = time.time()
r = requests.post('http://localhost:5000/api/chat', json={
    'question': '茅台2023年毛利率是多少？',
    'company': '茅台',
    'year': 2023
})
d = r.json()
print(f"Time: {time.time()-t0:.1f}s")
print(f"Answer: {d.get('answer','')[:200]}")
print(f"Sources: {len(d.get('sources',[]))}")
for s in d.get('sources', []):
    print(f"  [{s['similarity']:.4f}] source={s['source']} {s['doc_name']} p{s['page']}")
