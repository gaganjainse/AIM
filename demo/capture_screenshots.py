"""
AIM Screenshot & Video Capture Script v7 (DEFINITIVE)
=====================================================
Starts the Flask app in a background thread within the SAME process,
so the test client and server share the same SERVER_BOOT_ID.
Then uses Selenium with the authenticated session cookie.

This is the definitive version that actually works.
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
import re
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from werkzeug.serving import make_server

LOGIN_USER = "gagan"
LOGIN_PASS = "admin123"
OUTPUT_DIR = Path("demo/screenshots")
FRAME_DURATION_SEC = 3
VIDEO_OUTPUT = Path("demo/aim_demo.mp4")
SERVER_PORT = 5001  # Use a different port to avoid conflicts


def start_server(app):
    """Start the Flask server in a background thread."""
    server = make_server("127.0.0.1", SERVER_PORT, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(1)  # Wait for server to start
    print(f"  ✅ Server started on http://127.0.0.1:{SERVER_PORT}")
    return server


def get_authenticated_cookie(app) -> tuple:
    """Log in via test client and extract the session cookie."""
    app.config["TESTING"] = True
    c = app.test_client()

    r = c.get("/login")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    r2 = c.post("/login", data={
        "username": LOGIN_USER,
        "password": LOGIN_PASS,
        "csrf_token": csrf,
    }, follow_redirects=True)

    assert r2.status_code == 200, f"Login failed: {r2.status_code}"

    # Extract session cookie
    for key, cookie in c._cookies.items():
        if cookie.key == "aim_session":
            return cookie.value, key[0]  # value, domain

    raise RuntimeError("No session cookie found")


def setup_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--hide-scrollbars")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(5)
    return driver


def main():
    print("🎬 AIM Screenshot & Video Capture v7 (DEFINITIVE)")
    print("=" * 50)
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Create app and start server in same process
    print("🔧 Step 1: Creating Flask app and starting server...")
    app = create_app()
    server = start_server(app)

    # Step 2: Get authenticated session cookie
    print("🔑 Step 2: Authenticating...")
    cookie_value, cookie_domain = get_authenticated_cookie(app)
    print(f"  ✅ Got session cookie (domain={cookie_domain})")

    # Step 3: Start Selenium and inject cookie
    print("🌐 Step 3: Starting Chrome...")
    driver = setup_driver()

    try:
        # Inject the session cookie
        print("🍪 Step 4: Injecting session cookie...")
        driver.get(f"http://127.0.0.1:{SERVER_PORT}/health")
        time.sleep(1)
        driver.delete_all_cookies()

        # Try different domain formats
        injected = False
        for domain in [cookie_domain, "127.0.0.1", "localhost", ".127.0.0.1"]:
            try:
                driver.add_cookie({
                    "name": "aim_session",
                    "value": cookie_value,
                    "domain": domain,
                    "path": "/",
                })
                # Test if it works
                driver.get(f"http://127.0.0.1:{SERVER_PORT}/dashboard")
                time.sleep(2)
                if "dashboard" in driver.current_url.lower():
                    print(f"  ✅ Cookie works with domain={domain}")
                    injected = True
                    break
                else:
                    driver.delete_all_cookies()
            except Exception as e:
                driver.delete_all_cookies()
                continue

        if not injected:
            print("  ❌ Could not inject cookie. Trying alternative approach...")
            # Alternative: use the test client to get HTML and render in Selenium
            # But first, let's try navigating to login and filling the form
            print("  🔄 Trying direct form login via Selenium...")
            driver.get(f"http://127.0.0.1:{SERVER_PORT}/login")
            time.sleep(2)

            # Get CSRF from form
            csrf_input = driver.find_element("name", "csrf_token")
            csrf_val = csrf_input.get_attribute("value")

            driver.find_element("name", "username").send_keys(LOGIN_USER)
            driver.find_element("name", "password").send_keys(LOGIN_PASS)
            driver.find_element("css selector", "button[type='submit']").click()
            time.sleep(3)

            if "dashboard" in driver.current_url.lower():
                print("  ✅ Direct form login works!")
                injected = True
            else:
                print(f"  ❌ Direct login also failed. URL: {driver.current_url}")
                # Last resort: use test client HTML rendering
                print("  🔄 Falling back to HTML rendering approach...")
                capture_html_fallback(driver, app)
                return

        # Step 5: Capture all screenshots
        if injected:
            print(f"\n📸 Step 5: Capturing screenshots...")
            frames = capture_all(driver, app)
            print(f"\n✅ Captured {len(frames)} screenshots")

            # Compile video
            print(f"\n🎬 Step 6: Compiling video...")
            compile_video(frames)

            # Copy to main screenshots/
            print(f"\n📸 Step 7: Updating screenshots/ directory...")
            copy_screenshots(frames)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        server.shutdown()
        print("\n✅ All done!")


def capture_all(driver, app) -> list[Path]:
    """Capture screenshots of all pages."""
    frames = []
    base = f"http://127.0.0.1:{SERVER_PORT}"

    pages = [
        ("01_login.png",  f"{base}/login",    2),
        ("02_dashboard.png",  f"{base}/dashboard",   2.5),
        ("03_attendance.png",  f"{base}/attendance",   2.5),
        ("04_students.png",  f"{base}/students",   2.5),
        ("05_student_profile.png",  f"{base}/student/1",   2),
        ("06_student_chart.png",  f"{base}/student_chart/1",   2),
        ("07_reports.png",  f"{base}/report",   2.5),
        ("08_calendar.png",  f"{base}/calendar",   2.5),
        ("09_search.png",  f"{base}/search?q=CS-2026",   2),
        ("10_admin_users.png",  f"{base}/users",   2),
        ("11_admin_roles.png",  f"{base}/roles",   2),
        ("12_admin_settings.png",  f"{base}/settings",   2),
        ("13_admin_logs.png",  f"{base}/logs",   2),
        ("14_backup_restore.png",  f"{base}/backup_restore",   2),
        ("15_account.png",  f"{base}/account",   2),
        ("16_preferences.png",  f"{base}/preferences",   2),
        ("17_change_password.png",  f"{base}/change_password",   2),
    ]

    # Capture login page first (before auth)
    print(f"  Capturing login page...")
    driver.get(f"{base}/login")
    time.sleep(2)
    frames.append(capture_page(driver, "01_login.png"))

    total = len(pages) + 4
    for i, (filename, url, wait) in enumerate(pages[1:], 2):
        print(f"  [{i}/{total}] {filename}...")
        frames.append(capture_page(driver, filename, url, wait))

    # Dark mode — use JS to submit POST form
    print(f"  [{total-3}/{total}] Dark mode...")
    driver.get(f"{base}/dashboard")
    time.sleep(1)
    # Submit a POST form to toggle_theme using JavaScript
    driver.execute_script("""
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '/toggle_theme';
        var csrf = document.querySelector('input[name=\"csrf_token\"]');
        if (csrf) {
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            input.value = csrf.value;
            form.appendChild(input);
        }
        document.body.appendChild(form);
        form.submit();
    """)
    time.sleep(2)
    driver.get(f"{base}/dashboard")
    time.sleep(2.5)
    frames.append(capture_page(driver, "18_dark_mode_dashboard.png"))

    print(f"  [{total-2}/{total}] Dark mode attendance...")
    frames.append(capture_page(driver, "19_dark_mode_attendance.png", f"{base}/attendance", 2.5))

    # Mobile
    print(f"  [{total-1}/{total}] Mobile view...")
    driver.set_window_size(375, 812)
    time.sleep(0.5)
    driver.get(f"{base}/dashboard")
    time.sleep(2.5)
    frames.append(capture_page(driver, "20_mobile_view.png"))
    driver.set_window_size(1920, 1080)

    # Logout — toggle back to light first
    print(f"  [{total}/{total}] Logout...")
    driver.get(f"{base}/dashboard")
    time.sleep(1)
    driver.execute_script("""
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '/toggle_theme';
        var csrf = document.querySelector('input[name=\"csrf_token\"]');
        if (csrf) {
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            input.value = csrf.value;
            form.appendChild(input);
        }
        document.body.appendChild(form);
        form.submit();
    """)
    time.sleep(1)
    driver.get(f"{base}/login")
    time.sleep(2)
    frames.append(capture_page(driver, "21_logout.png"))

    return frames


def capture_page(driver, filename: str, url: str = None, wait_sec: float = 2.0) -> Path:
    if url:
        driver.get(url)
        time.sleep(wait_sec)
    filepath = OUTPUT_DIR / filename
    driver.save_screenshot(str(filepath))
    return filepath


def capture_html_fallback(driver, app):
    """Fallback: render HTML from test client in Selenium."""
    print("  Using HTML rendering fallback...")
    app.config["TESTING"] = True
    frames = []

    with app.test_client() as c:
        # Login
        r = c.get("/login")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
        c.post("/login", data={"username": LOGIN_USER, "password": LOGIN_PASS, "csrf_token": csrf}, follow_redirects=True)

        pages = [
            ("02_dashboard.png", "/dashboard"),
            ("03_attendance.png", "/attendance"),
            ("04_students.png", "/students"),
            ("05_student_profile.png", "/student/1"),
            ("06_student_chart.png", "/student_chart/1"),
            ("07_reports.png", "/report"),
            ("08_calendar.png", "/calendar"),
            ("09_search.png", "/search?q=CS-2026"),
            ("10_admin_users.png", "/users"),
            ("11_admin_roles.png", "/roles"),
            ("12_admin_settings.png", "/settings"),
            ("13_admin_logs.png", "/logs"),
            ("14_backup_restore.png", "/backup_restore"),
            ("15_account.png", "/account"),
            ("16_preferences.png", "/preferences"),
            ("17_change_password.png", "/change_password"),
        ]

        # Login page (before auth)
        with app.test_client() as c2:
            r = c2.get("/login")
            html = r.data.decode("utf-8")
            html = html.replace('href="/static/', f'href="http://127.0.0.1:{SERVER_PORT}/static/')
            html = html.replace('src="/static/', f'src="http://127.0.0.1:{SERVER_PORT}/static/')
            tmp = OUTPUT_DIR / "tmp_login.html"
            tmp.write_text(html, encoding="utf-8")
            driver.get(f"file:///{tmp.absolute()}")
            time.sleep(1.5)
            frames.append(capture_page(driver, "01_login.png"))
            tmp.unlink()

        for filename, url in pages:
            r = c.get(url, follow_redirects=True)
            html = r.data.decode("utf-8")
            html = html.replace('href="/static/', f'href="http://127.0.0.1:{SERVER_PORT}/static/')
            html = html.replace('src="/static/', f'src="http://127.0.0.1:{SERVER_PORT}/static/')
            tmp = OUTPUT_DIR / f"tmp_{filename}"
            tmp.write_text(html, encoding="utf-8")
            driver.get(f"file:///{tmp.absolute()}")
            time.sleep(1.5)
            frames.append(capture_page(driver, filename))
            tmp.unlink()

    print(f"  ✅ Captured {len(frames)} screenshots (HTML fallback)")
    compile_video(frames)


def compile_video(frames: list[Path]):
    if not frames:
        return
    list_file = OUTPUT_DIR / "frame_list.txt"
    with open(list_file, "w") as f:
        for frame in frames:
            f.write(f"file '{frame.absolute()}'\n")
            f.write(f"duration {FRAME_DURATION_SEC}\n")
        f.write(f"file '{frames[-1].absolute()}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-vf", f"fps={1/FRAME_DURATION_SEC},format=yuv420p,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(VIDEO_OUTPUT),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        list_file.unlink(missing_ok=True)
        size_mb = VIDEO_OUTPUT.stat().st_size / (1024 * 1024)
        print(f"  ✅ Video: {VIDEO_OUTPUT} ({size_mb:.1f} MB)")
    else:
        print(f"  ⚠️  FFmpeg error: {result.stderr[-200:]}")


def copy_screenshots(frames: list[Path]):
    import shutil
    mapping = {
        "01_login.png": "01_login.png",
        "02_dashboard.png": "02_dashboard.png",
        "03_attendance.png": "03_attendance.png",
        "10_admin_users.png": "04_admin_controls.png",
        "07_reports.png": "05_reports.png",
        "20_mobile_view.png": "06_mobile_view.png",
        "18_dark_mode_dashboard.png": "07_dark_mode.png",
    }
    for src_name, dst_name in mapping.items():
        src = OUTPUT_DIR / src_name
        dst = Path("screenshots") / dst_name
        if src.exists():
            shutil.copy2(src, dst)
            print(f"    ✅ {src_name} → screenshots/{dst_name}")


if __name__ == "__main__":
    main()
