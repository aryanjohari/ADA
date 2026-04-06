# Wakeup — first user message (boot)

Run a quick **hardware / OS check** using only `run_allowlisted_shell` with commands from `shell_allowlist.txt` (exact strings). Run at least:

- `uname -a`
- `cat /proc/cpuinfo` (or a shorter allowlisted probe if output is huge)
- `free -h`

Then **greet the operator in one short paragraph**: who you are (ADA), that you are running locally, and one or two concrete facts from the probes (arch/kernel, cores, RAM headroom if visible).
