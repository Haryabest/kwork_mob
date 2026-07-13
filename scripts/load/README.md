"""
Load harness §21 / DoD: 50 members + 100 orders + shoot_link.

Запуск (дома):
  k6 run scripts/load/k6_b2b.js -e BASE_URL=http://localhost:8000 -e TOKEN=... -e COMPANY_ID=1
  locust -f scripts/load/locustfile.py --host=http://localhost:8000
"""
