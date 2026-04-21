# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install deps and run:

```
pip install -r requirements.txt
python main.py
```

There is no test suite, linter, or build step. Edit search parameters directly in `main.py` (search_keys, number_of_images, headless, min/max_resolution, max_missed, number_of_workers, keep_filenames) before running.

Important: per the README, the program must be invoked from a terminal, not from inside VSCode's integrated runner — Chrome/driver interaction misbehaves otherwise.

## Architecture

Three-module Selenium-driven scraper. Flow: `main.py` → `GoogleImageScraper` → `patch` (chromedriver bootstrap).

- **`main.py`** — entrypoint. Builds `webdriver_path = ./webdriver/<exe>` and `image_path = ./photos`, then fans out one `GoogleImageScraper` instance per search key across a `ThreadPoolExecutor`. Each worker calls `find_image_urls()` then `save_images()`. One worker per search term — workers are not reusable across keys.

- **`GoogleImageScraper.py`** — the scraping engine. Two-phase design:
  1. **URL discovery (`find_image_urls`)** — drives `https://www.google.com/search?...&tbm=isch`, walks result thumbnails via an XPath template (`//*[@id="rso"]/div/.../div[%s]/div[2]/h3/a/.../g-img`) using nested `indx_1`/`indx_2` counters, clicks each to open the side panel, then reads the full-resolution `src` from whichever of the class-name candidates `["n3VNCb","iPVvYb","r48jcc","pT0Scc","H8Rx8c"]` Google is currently using. This class-name list and XPath are the **load-bearing brittleness of the project** — Google changes its Images DOM periodically and the recent commits in `git log` are almost all "updated code to work with new google search interface" fixes. When the scraper stops returning URLs, suspect this list first.
  2. **Download (`save_images`)** — `requests.get` each URL, open via Pillow, optionally re-derive filename from the URL basename, drop images outside the `min_resolution`/`max_resolution` box by deleting after save.

  `max_missed` gates the discovery loop — after that many consecutive XPath misses the scraper assumes it has run off the end of results and exits. Bump it for long queries.

- **`patch.py`** — chromedriver installer. `download_lastest_chromedriver(version="")` hits `https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json`, picks the platform-specific zip (`linux64`/`mac-x64`/`win32`), extracts into `./webdriver/`, and chmods executable. Invoked in two places in `GoogleImageScraper.__init__`: once if the driver file is missing, and once in the `except` branch of the initial `driver = webdriver.Chrome(...)` attempt — in that branch it parses the installed-Chrome version out of the Selenium error message via regex `(\d+\.\d+\.\d+\.\d+)` to pin the matching driver. That self-healing path is what the `4d9d89a` commit is about; keep it working when touching `patch.py`.

## Version pinning notes

`requirements.txt` pins `selenium==3.141.0`. The scraper uses the legacy `webdriver.Chrome(webdriver_path, chrome_options=options)` signature — Selenium 4 renamed this to `service=Service(webdriver_path)` and `options=`. Upgrading Selenium requires updating the constructor call in `GoogleImageScraper.__init__`.
