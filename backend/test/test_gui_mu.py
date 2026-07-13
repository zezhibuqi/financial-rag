import requests

r = requests.post('http://localhost:5000/api/chat', json={
    'question': '宁德时代2025年归母净利润是多少'
})
d = r.json()
print("Answer:", d['answer'][:300])
print(f"Sources: {len(d['sources'])}")
for s in d['sources']:
    print(f"  [{s['similarity']:.4f}] {s['source']} {s['doc_name']} p{s['page']}")
    print(f"    {s['snippet'][:100]}")
    print()
