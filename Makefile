# Thin convenience wrappers for Pi operator scripts — see docs/CHEATSHEET.md
.PHONY: cheatsheet-open smoke ingest-day daemon-help

cheatsheet-open:
	@[ -n "$$PAGER" ] && exec $$PAGER docs/CHEATSHEET.md || exec less docs/CHEATSHEET.md

smoke:
	./scripts/pi/smoke.sh

ingest-day:
	./scripts/pi/ingest-day.sh

daemon-help:
	./scripts/pi/daemon-help.sh
