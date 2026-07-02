"""Golden Set 线上验收测试"""
import requests, time

BACKEND = 'https://backend-liard-pi-99.vercel.app'

tests = [
    {
        "name": "茅台 2023 毛利率",
        "body": {"question": "茅台2023年毛利率是多少？", "company": "茅台", "year": 2023},
        "expect": "92.11",
    },
    {
        "name": "宁茅 2024 利润比较",
        "body": {"question": "宁德时代和茅台2024年谁的利润更高"},
        "expect": "茅台",
    },
    {
        "name": "宁德 2023-2025 经营现金流",
        "body": {"question": "宁德时代2023年到2025年的经营活动现金流净额分别是多少"},
        "expect": "1332",
    },
]

for t in tests:
    t0 = time.time()
    r = requests.post(f'{BACKEND}/api/chat', json=t['body'], timeout=60)
    d = r.json()
    dt = time.time() - t0
    passed = t['expect'] in d.get('answer', '')
    status = '✅' if passed else '❌'
    print(f"{status} {t['name']} ({dt:.1f}s)")
    if not passed:
        print(f"   Answer: {d.get('answer','')[:150]}")
    print(f"   Sources: {len(d.get('sources',[]))}")
