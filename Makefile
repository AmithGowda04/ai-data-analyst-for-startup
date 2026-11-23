.PHONY: setup adspend test
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
adspend:
	python data_gen/generate_ad_spend.py --out ad_spend.csv
test:
	pytest -q
