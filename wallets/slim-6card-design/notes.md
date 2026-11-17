# slim-6card-design: notes

- **What this is:** a generated bifold design (shell 197.7 x 87 mm, 6 card slots, 1.0 mm shell, 0.7 mm slot leather), taken from the leather-patterns workspace
  you uploaded (`out_wallets/slim_6card`). It is **not** a photographed wallet, and it is **not** an MA+ wallet: nothing in that workspace mentions MA+.
- **Why it is here:** to run the record -> simulation -> report pipeline end to end on something concrete while no real wallet has been captured.
  The report it produces says "design" everywhere a number is only what the design asks for.
- **To replace it:** photograph a real wallet as in `docs/CAPTURE.md` (an edge-on photo of the closed spine matters most), measure the closed thickness, the shell thickness and
  the layers at the spine, and put the numbers in a new `wallets/<slug>/wallet.yaml` with `source: measured`.
- `source/` holds the two design files the numbers come from (`report.json`, `pattern.svg`).
