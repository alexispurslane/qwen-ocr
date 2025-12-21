install:
    (uv sync)

check:
    (uv run ty check .)

web-debug:
    (cd frontend/ && deno run dev)

web-build:
    (cd frontend/ && deno run build)

debug:
    just check
    just web-debug &
    (OCR_DEBUG=True uv run src/main.py)

run:
    just check
    just web-build
    (cd src && uv run src/main.py)
