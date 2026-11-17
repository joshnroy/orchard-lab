"""End-to-end test: plays two full rounds in headless Chromium.

Usage: python tests/e2e.py [base_url] [screenshot_dir]
Needs: pip install playwright && playwright install chromium
"""
import os, sys, json, glob
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
from apple_env import params_from_seed  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
SHOTS = sys.argv[2] if len(sys.argv) > 2 else "screenshots"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(SHOTS, exist_ok=True)
errors = []


def clear_dialog(page):
    """Click through the advisor's dialogue until it closes."""
    for _ in range(40):
        if not page.is_visible("#dialog"):
            return
        page.click("#dialog")
        page.wait_for_timeout(60)
    raise AssertionError("dialogue never closed")


def close_rules(page):
    page.wait_for_selector("#rules-ok")
    text = page.inner_text("#rulesTxt")
    assert "DEMO" in text and "DEFEND" in text, text
    page.click("#rules-ok")


def wait_ready(page):
    page.wait_for_function("!document.querySelector('#act-done').disabled")


def apples(page):
    return int(page.inner_text("#crateCount"))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 900}, accept_downloads=True)
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))

    before = set(glob.glob(os.path.join(DATA_DIR, "*.json")))
    page.goto(BASE + "/?setup=1&debug=1")
    page.fill("#f-n", "20")
    page.fill("#f-rounds", "2")
    page.fill("#f-k", "0.1, 0.3")
    page.fill("#f-lr", "0.1")
    page.fill("#f-seed", "42")
    page.click("#f-demo button[data-v='3']")
    page.screenshot(path=f"{SHOTS}/01_setup.png", full_page=True)
    page.click("#btn-start")

    # ---- round 1: practice, demo, review(3), defend
    clear_dialog(page); close_rules(page); wait_ready(page)
    assert apples(page) == 20
    page.click("#act-practice"); wait_ready(page)
    assert apples(page) == 19, apples(page)
    page.click("#act-demo"); wait_ready(page)
    assert apples(page) == 17, apples(page)
    assert "k = 0.500" in page.inner_text("#debug"), page.inner_text("#debug")  # 0.1 + 0.1 + 3*0.1
    page.click("#act-eval"); page.fill("#m-val", "3"); page.click("#m-go")
    page.wait_for_selector("#r-ok:not(.hidden)")
    assert "of 3" in page.inner_text("#rres")
    page.screenshot(path=f"{SHOTS}/02_review.png")
    page.click("#r-ok"); wait_ready(page)
    assert apples(page) == 14, apples(page)
    page.screenshot(path=f"{SHOTS}/03_play.png", full_page=True)
    page.click("#act-done"); page.click("#d-yes")
    page.wait_for_selector("#r-ok:not(.hidden)", timeout=10000)
    page.screenshot(path=f"{SHOTS}/04_defense.png")
    page.click("#r-ok")

    # ---- round 2: defend immediately; starting skill should be 0.3
    clear_dialog(page); close_rules(page); wait_ready(page)
    assert apples(page) == 20 and "k = 0.300" in page.inner_text("#debug")
    page.click("#act-done"); page.click("#d-yes")
    page.wait_for_selector("#r-ok:not(.hidden)", timeout=10000)
    page.click("#r-ok"); clear_dialog(page)

    # ---- final screen + data
    page.wait_for_selector("#screen-final:not(.hidden)")
    page.wait_for_function("document.querySelector('#saveStatus').textContent.length > 0")
    status = page.inner_text("#saveStatus")
    assert "Saved" in status, status
    assert page.is_visible("#btn-again")  # researcher mode can start another game
    page.screenshot(path=f"{SHOTS}/05_final.png", full_page=True)
    with page.expect_download() as d:
        page.click("#dl-csv")
    csv = open(d.value.path()).read().strip().splitlines()
    assert len(csv) == 1 + 5, csv  # header + 4 steps in round 1 + 1 in round 2

    new = set(glob.glob(os.path.join(DATA_DIR, "*.json"))) - before
    assert new, "server did not write a data file"
    saved = json.load(open(sorted(new)[-1]))
    r1, r2 = saved["rounds"]
    assert [s["action"] for s in r1["steps"]] == ["practice", "demo", "review", "defend"]
    assert saved["pid"].startswith("p_") and len(saved["pid"]) == 14 and saved["started"], saved["pid"]
    assert r1["final"]["apples_tested"] == 14 and r2["final"]["apples_tested"] == 20
    for f in new:
        os.remove(f)  # don't leave test data behind

    # ---- phone layout: no horizontal scroll
    m = browser.new_page(viewport={"width": 390, "height": 844})
    m.goto(BASE + "/")
    clear_dialog(m); close_rules(m); wait_ready(m)
    overflow = m.evaluate("document.documentElement.scrollWidth - innerWidth")
    m.screenshot(path=f"{SHOTS}/06_mobile.png", full_page=True)
    assert overflow <= 0, f"horizontal overflow {overflow}px on phone"

    # ---- participant mode (plain URL): no setup screen, URL can't change the study settings
    g = browser.new_page(viewport={"width": 1100, "height": 900})
    g.goto(BASE + "/?n=12&k=0.9&demo=off&debug=1")
    assert not g.is_visible("#screen-setup")
    clear_dialog(g); rules = g.inner_text("#rulesTxt")
    assert "DEMO" in rules and "20 apples" in rules and "PhD student" in rules, rules
    g.click("#rules-ok"); wait_ready(g)
    assert apples(g) == 20 and g.is_visible("#act-demo") and not g.is_visible("#debug")
    g.click("#act-done"); g.click("#d-yes")
    g.wait_for_selector("#r-ok:not(.hidden)", timeout=10000); g.click("#r-ok"); clear_dialog(g)
    g.wait_for_selector("#screen-final:not(.hidden)")
    assert not g.is_visible("#btn-again")
    g.wait_for_function("document.querySelector('#saveStatus').textContent.length > 0")
    new = set(glob.glob(os.path.join(DATA_DIR, "*.json"))) - before
    for f in new:
        d = json.load(open(f))
        pr = d["rounds"][0]["params"]
        assert d["pid"].startswith("p_") and d["mode"] == "participant" and d["config"]["paramsFrom"] == "seed"
        assert {k: pr[k] for k in ("k0", "lr", "demoMult")} == params_from_seed(pr["seed"]), pr
        os.remove(f)
    browser.close()

assert not errors, errors
print("E2E PASSED: rounds", r1["final"]["score"], r2["final"]["score"], "| screenshots in", SHOTS)
