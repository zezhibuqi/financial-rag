"""测试跨公司比较查询"""
import requests, time

t0 = time.time()
r = requests.post('http://localhost:5000/api/chat', json={
    'question': '宁德时代和茅台2024年谁的利润更高'
})
d = r.json()
print(f"Time: {time.time()-t0:.1f}s")
print(f"Answer: {d.get('answer','')[:300]}")
print(f"Sources: {len(d.get('sources',[]))}")
for s in d.get('sources', []):
    print(f"  [{s['similarity']:.4f}] source={s['source']} {s['doc_name']} p{s['page']}")
