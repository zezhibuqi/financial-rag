import requests
r = requests.post('http://localhost:5000/api/chat', json={
    'question': '宁德时代2023年到2025年的经营活动现金流净额分别是多少'
})
d = r.json()
print(d['answer'][:400])
print(f"Sources: {len(d['sources'])}")
for s in d['sources']:
    print(f"  [{s['similarity']:.4f}] {s['source']} {s['doc_name']} p{s['page']}")
