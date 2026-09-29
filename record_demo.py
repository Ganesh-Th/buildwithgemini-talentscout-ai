import os
import time
import shutil
import glob
import subprocess
from playwright.sync_api import sync_playwright

VIDEO_DIR = "demo_raw"
OUTPUT_MP4 = "demo_video.mp4"

if os.path.exists(VIDEO_DIR):
    shutil.rmtree(VIDEO_DIR)
os.makedirs(VIDEO_DIR, exist_ok=True)

print("Starting browser and video recording...")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=VIDEO_DIR,
        record_video_size={"width": 1280, "height": 720}
    )
    page = context.new_page()

    # 1. Open the app
    print("Navigating to http://localhost:8080...")
    page.goto("http://localhost:8080", wait_until="networkidle")
    
    # Authenticate mock user so workspace, dark mode, and history are visible
    page.evaluate('''() => {
        currentUser = {
            email: "alex.scout@example.com",
            name: "Alex Scout",
            picture: "",
            sub: "demo_user_123"
        };
        updateUserUI();
        
        // Ensure default dark mode
        document.body.classList.add("dark-mode");
    }''')
    time.sleep(2)

    # 2. Showcase Dark / Light mode toggle
    print("Showcasing Theme Toggle...")
    theme_btn = page.locator("#theme-toggle-btn")
    theme_btn.hover()
    time.sleep(1)
    theme_btn.click() # Switches to Light mode
    time.sleep(2)
    theme_btn.click() # Switches back to Dark mode
    time.sleep(1.5)

    # 3. Showcase Candidate Profile Modal
    print("Opening Profile Modal...")
    page.evaluate("openProfileModal()")
    time.sleep(3)
    page.evaluate("closeProfileModal()")
    time.sleep(1)

    # 4. First prompt: Click the "Live AI/ML Jobs" prompt chip
    print("Clicking prompt chip 1: Live AI/ML Jobs...")
    chip1 = page.locator(".prompt-chip").first
    chip1.hover()
    time.sleep(0.6)
    chip1.click()

    # Wait for the agent to finish loading and render the A2UI jobs card
    print("Waiting for live jobs card to render...")
    page.wait_for_selector(".loading-dots", state="detached", timeout=60000)
    time.sleep(1)
    
    # Scroll down to show full jobs card
    page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
    time.sleep(5)  # Showcase the live jobs card

    # 5. Second prompt: Richer prompt with DB search and Image Generation
    print("Typing prompt 2: Tech conferences in SF + banner generation...")
    input_box = page.locator("#input")
    input_box.click()
    prompt2 = "Search tech conferences in SF and generate a banner image for the top event."
    for char in prompt2:
        input_box.type(char, delay=25)
    time.sleep(0.8)
    
    # Click send button
    page.locator("#form button[type='submit']").click()

    # Wait for the second response (with DB search and Image Generation)
    print("Waiting for prompt 2 response with database lookup & image...")
    page.wait_for_selector(".loading-dots", state="detached", timeout=75000)
    
    # Smooth scroll down to display the new card and generated banner
    for _ in range(6):
        page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
        time.sleep(0.5)
        
    time.sleep(6)  # Showcase the conference card and generated artwork

    print("Closing browser context to finalize video...")
    page.close()
    context.close()
    browser.close()

# Find the recorded webm file
webm_files = glob.glob(f"{VIDEO_DIR}/*.webm")
if not webm_files:
    raise RuntimeError("No recorded video found in demo_raw!")

raw_webm = webm_files[0]
print(f"Recorded raw video: {raw_webm}")

# Probe video duration using ffprobe
ffprobe_cmd = [
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", raw_webm
]
video_duration = float(subprocess.check_output(ffprobe_cmd).decode().strip())
print(f"Video duration: {video_duration:.1f}s")

# Combine video and upbeat lo-fi background music with audio fade-out
fade_out_start = max(0, video_duration - 2.5)
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-i", raw_webm,
    "-stream_loop", "-1", "-i", "lofi_beat.wav",
    "-c:v", "libx264", "-preset", "fast", "-crf", "22",
    "-filter:a", f"volume=0.85,afade=t=out:st={fade_out_start:.1f}:d=2.5",
    "-c:a", "aac", "-b:a", "192k",
    "-t", f"{video_duration:.2f}",
    OUTPUT_MP4
]
print("Muxing video with upbeat lo-fi audio...")
subprocess.run(ffmpeg_cmd, check=True)

print(f"Demo video created successfully: {OUTPUT_MP4}")
