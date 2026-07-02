import requests, time

r = requests.post('http://localhost:5000/api/chat', json={
    'question': '宁德时代和贵州茅台2023年、2024年、2025年的营业收入分别是多少？谁的营收规模更大？'
})
d = r.json()
print(d['answer'][:500])
print(f"\nSources: {len(d['sources'])}")
for s in d['sources']:
    print(f"  [{s['similarity']:.4f}] {s['source']} {s['doc_name']} p{s['page']}")
