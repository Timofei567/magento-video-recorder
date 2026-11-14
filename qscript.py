"""
Browser scenario used by capture_video.py.

Requires Python 3.9+ and Playwright's synchronous API.
"""

import re
import time
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
)


PATH_TO_VIDEO_FOLDER = "./video"

VIEWPORT = {"width": 1280, "height": 720}
NAVIGATION_TIMEOUT_MS = 45000
RESULT_TIMEOUT_MS = 45000

def _safe_filename(value):
    """Convert a company name into a filesystem-safe filename."""

    value = (value or "recording").strip()

    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)

    value = re.sub(r"\s+", "_", value)

    return value[:120] or "recording"


def _smooth_move(page, start, end, duration=0.8, steps=30):
    """Move the real Playwright mouse in small increments."""

    startx, starty = start
    endx, endy = end

    for index in range(1, steps + 1):
        t = index / steps

        eased = t * t * (3 - 2 * t)

        x = startx + (endx - startx) * eased
        y = starty + (endy - starty) * eased

        page.mouse.move(x, y)
        time.sleep(duration / steps)


def _show_callout(
    page,
    text,
    bg_color="#ffeb3b",
    text_color="#111111",
    fade=True,
):
    """Display a compact annotation near the top of the page."""

    page.evaluate(
        """({text, bgColor, textColor, fade}) => {
            const old = document.getElementById('__capture_callout');

            if (old) {
                old.remove();
            }

            const el = document.createElement('div');
            el.id = '__capture_callout';
            el.textContent = text;

            Object.assign(el.style, {
                position: 'fixed',
                top: '22px',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: '2147483647',
                background: bgColor,
                color: textColor,
                padding: '12px 20px',
                border: '2px solid #111',
                borderRadius: '4px',
                font: '16pt Arial, sans-serif',
                boxShadow: '0 3px 12px rgba(0,0,0,.28)',
                pointerEvents: 'none',
                whiteSpace: 'pre-wrap',
                maxWidth: '85vw',
                opacity: fade ? '0' : '1',
                transition: 'opacity 2s ease'
            });

            document.documentElement.appendChild(el);

            if (fade) {
                requestAnimationFrame(() => {
                    el.style.opacity = '1';
                });
            }
        }""",
        {
            "text": str(text),
            "bgColor": bg_color,
            "textColor": text_color,
            "fade": bool(fade),
        },
    )

    time.sleep(2.1)


def _install_visual_effects(context):
    """Install an SVG cursor, yellow highlight and click ripples."""

    context.add_init_script(
        r"""
        (() => {
            const install = () => {

                if (
                    !document.documentElement ||
                    document.getElementById('__capture_cursor')
                ) {
                    return;
                }

                const style = document.createElement('style');

                style.textContent = `
                    #__capture_highlight {
                        position: fixed;
                        left: 0;
                        top: 0;
                        width: 64px;
                        height: 64px;
                        border-radius: 50%;
                        background: rgba(255, 220, 0, 0.38);
                        transform: translate(-50%, -50%);
                        z-index: 2147483645;
                        pointer-events: none;
                    }

                    #__capture_cursor {
                        position: fixed;
                        left: 0;
                        top: 0;
                        width: 32px;
                        height: 32px;
                        z-index: 2147483647;
                        pointer-events: none;
                        transform: translate(-2px, -2px);
                        filter: drop-shadow(
                            1px 1px 1px rgba(0,0,0,.25)
                        );
                    }

                    .__capture_ripple {
                        position: fixed;
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        border: 3px solid rgba(20, 120, 255, .85);
                        background: rgba(80, 170, 255, .18);
                        z-index: 2147483646;
                        pointer-events: none;
                        transform: translate(-50%, -50%) scale(.2);
                        animation: __capture_ripple_anim .65s ease-out forwards;
                    }

                    @keyframes __capture_ripple_anim {
                        to {
                            transform: translate(-50%, -50%) scale(3.2);
                            opacity: 0;
                        }
                    }
                `;

                document.documentElement.appendChild(style);


                const highlight = document.createElement('div');

                highlight.id = '__capture_highlight';

                Object.assign(highlight.style, {
                    position: 'fixed',
                    left: '0px',
                    top: '0px',
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    background: 'rgba(255, 220, 0, 0.38)',
                    transform: 'translate(-50%, -50%)',
                    pointerEvents: 'none',
                    zIndex: '2147483645'
                });

                document.documentElement.appendChild(highlight);


                const cursor = document.createElementNS(
                    'http://www.w3.org/2000/svg',
                    'svg'
                );

                cursor.setAttribute('id', '__capture_cursor');
                cursor.setAttribute('viewBox', '0 0 32 32');

                cursor.innerHTML = `
                    <path
                        d="M3 2 L3 26 L10 19 L15 29 L20 26 L15 16 L26 16 Z"
                        fill="white"
                        stroke="black"
                        stroke-width="1.8"
                        stroke-linejoin="round"
                    />
                `;

                document.documentElement.appendChild(cursor);


                document.addEventListener(
                    'mousemove',
                    (event) => {
                        const x = event.clientX;
                        const y = event.clientY;

                        highlight.style.left = x + 'px';
                        highlight.style.top = y + 'px';

                        cursor.style.left = x + 'px';
                        cursor.style.top = y + 'px';
                    },
                    true
                );


                document.addEventListener(
                    'click',
                    (event) => {
                        const ripple = document.createElement('span');

                        ripple.className = '__capture_ripple';

                        ripple.style.left = event.clientX + 'px';
                        ripple.style.top = event.clientY + 'px';

                        document.documentElement.appendChild(ripple);

                        ripple.addEventListener(
                            'animationend',
                            () => ripple.remove(),
                            { once: true }
                        );
                    },
                    true
                );
            };


            if (document.readyState === 'loading') {
                document.addEventListener(
                    'DOMContentLoaded',
                    install,
                    { once: true }
                );
            } else {
                install();
            }
        })();
        """
    )


def _check_duckduckgo_error(page):


    error_texts = [
        "Unexpected error. Please try again",
        "Our support email address includes an anonymized error code",
    ]

    for error_text in error_texts:
        try:
            error_message = page.get_by_text(
                error_text,
                exact=False,
            ).first

            if error_message.is_visible(timeout=1000):
                return True

        except PlaywrightTimeoutError:
            continue

        except PlaywrightError:
            continue

    return False


def _wait_for_search_results(page):


    result = page.locator(
        'a[data-testid="result-title-a"]'
    ).first

    deadline = time.monotonic() + (RESULT_TIMEOUT_MS / 1000)

    while time.monotonic() < deadline:

        if _check_duckduckgo_error(page):
            raise RuntimeError(
                "DuckDuckGo returned an error instead of search results. "
                "The search may have been temporarily restricted."
            )

        try:
            if result.is_visible(timeout=1000):
                return result

        except PlaywrightTimeoutError:
            pass

        except PlaywrightError:
            pass

        page.wait_for_timeout(500)

    if _check_duckduckgo_error(page):
        raise RuntimeError(
            "DuckDuckGo returned an error instead of search results."
        )

    raise RuntimeError(
        f"Search results did not appear within {RESULT_TIMEOUT_MS} ms."
    )


def CaptureVideo_Magento(
    url,
    company_name,
    language,
    country,
    postcode,
    city,
    street,
    house_no,
):
    """
    Record one browser session.

    Returns the absolute path to the .webm file, or None if recording fails.
    All arguments are strings, as supplied by csv.DictReader.
    """

    output_dir = Path(PATH_TO_VIDEO_FOLDER).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    final_path = output_dir / (
        _safe_filename(company_name) + ".webm"
    )

    temp_video_path = None
    context = None
    browser = None

    try:
        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(
                headless= False
            )

            context = browser.new_context(
                viewport=VIEWPORT,
                record_video_dir=str(output_dir),
                record_video_size=VIEWPORT,
                device_scale_factor=1,
            )

            _install_visual_effects(context)

            page = context.new_page()

            page.set_default_timeout(15000)

            page.set_default_navigation_timeout(
                NAVIGATION_TIMEOUT_MS
            )


            target_url = (
                (url or "").strip()
                or "https://duckduckgo.com/"
            )

            _show_callout(page, "Opening website")

            page.goto(
                target_url,
                wait_until="domcontentloaded",
            )

            page.wait_for_timeout(1200)
            
            search_box = page.locator(
                'textarea[name="q"]'
            ).first

            search_box.wait_for(
                state="visible",
                timeout=20000,
            )

            box = search_box.bounding_box()

            if not box:
                raise RuntimeError(
                    "Search field is visible but has no bounding box."
                )


            current = page.evaluate(
                "() => ({x: 0, "
                "y: 0})"
            )

            mouse_position = (
                current["x"],
                current["y"],
            )

            destination = (
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2,
            )


            _smooth_move(
                page,
                mouse_position,
                destination,
            )

            mouse_position = destination

            search_box.click()

            page.wait_for_timeout(350)


            query = (
                "Magento developer in "
                + (city or "").strip()
            )

            page.keyboard.type(
                query,
                delay=105,
            )

            page.wait_for_timeout(500)


            search_button = page.locator(
                'form button[type="submit"]'
            ).first

            if (
                search_button.count()
            ):

                button_box = search_button.bounding_box()

                if button_box:

                    button_point = (
                        button_box["x"] + button_box["width"] / 2 + 40,
                        button_box["y"] + button_box["height"] / 2,
                    )
                    _smooth_move(
                        page,
                        mouse_position,
                        button_point,
                        duration=0.55,
                    )

                    mouse_position = button_point



            try:
                    page.mouse.click(button_box["x"] + button_box["width"] / 2 + 40, button_box["y"] + button_box["height"] / 2)
                    search_box.press(
                        "Enter",
                        timeout=70,
                        no_wait_after=True,
                    )

            except PlaywrightError as enter_error:

                    print(
                        "[WARNING] Enter submission failed: "
                        f"{enter_error}"
                    )


            if _check_duckduckgo_error(page):

                raise RuntimeError(
                    "DuckDuckGo displayed: "
                    "Unexpected error. Please try again. "
                    "This is a DuckDuckGo response, not a Python error."
                )


            result = _wait_for_search_results(page)

            page.wait_for_timeout(900)


            result.scroll_into_view_if_needed(
                timeout=10000
            )

            result_box = result.bounding_box()

            if not result_box:
                raise RuntimeError(
                    "The first search result has no bounding box."
                )


            result_point = (
                result_box["x"] + result_box["width"] / 2,
                result_box["y"] + result_box["height"] / 2,
            )



            mouse_position = (0, 0)
            _smooth_move(
                page,
                mouse_position,
                result_point,
                duration=0.9,
                steps=36,
            )


            page.mouse.click(
                result_point[0],
                result_point[1],
            )


            # Wait for the clicked result to finish navigating, then keep
            # the destination page visible for about 2 seconds.
            try:
                page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=NAVIGATION_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError:
                # Some sites keep loading in the background; the destination
                # can still be usable, so preserve the recording pause.
                pass

            page.wait_for_timeout(2000)


            video = page.video

            context.close()
            context = None

            temp_video_path = Path(
                video.path()
            ).resolve()


            if browser:
                browser.close()
                browser = None


        if (
            temp_video_path is None
            or not temp_video_path.exists()
        ):
            raise RuntimeError(
                "Playwright did not produce a video file."
            )

        if temp_video_path.stat().st_size == 0:
            raise RuntimeError(
                "The recorded video file is empty."
            )


        if final_path.exists():

            stem = final_path.stem
            suffix = final_path.suffix

            counter = 2

            while (
                output_dir / f"{stem}_{counter}{suffix}"
            ).exists():

                counter += 1

            final_path = (
                output_dir / f"{stem}_{counter}{suffix}"
            )


        temp_video_path.replace(final_path)

        print(
            f"[SUCCESS] Video saved: {final_path}"
        )

        return str(final_path)


    except Exception as exc:

        print(
            f"[ERROR] {company_name or 'Unknown company'}: {exc}"
        )

        return None


    finally:

        if context is not None:

            try:
                context.close()

            except Exception:
                pass


        if browser is not None:

            try:
                browser.close()

            except Exception:
                pass