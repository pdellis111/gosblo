PORT ?= 8081

.PHONY: test serve live

test:
	python3 -m unittest discover -s tests -v

serve:
	python3 -m http.server $(PORT) --directory site

live:
	python3 scripts/live_server.py --port $(PORT) --directory site
