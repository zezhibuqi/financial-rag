"""测试 /api/docs 端点"""
import requests

r = requests.get('http://localhost:5000/api/docs')
d = r.json()
print(f"Companies: {d.get('companies')}")
print(f"Years: {d.get('years')}")
print(f"Docs: {len(d.get('docs', []))}")
for doc in sorted(d.get('docs', []), key=lambda x: (x['company'], x['year'])):
    print(f"  {doc['company']} {doc['year']}: {doc['chunk_count']} chunks")
