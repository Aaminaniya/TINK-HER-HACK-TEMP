import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

pyautogui.FAILSAFE = False
cap = cv2.VideoCapture(0)

# ------------------ Optimized Resolution ------------------
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

cv2.namedWindow("Invisible Mouse - Ultra Smooth", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Invisible Mouse - Ultra Smooth", 1280, 720)

# ------------------ MediaPipe Hands ------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# ------------------ Screen Settings ------------------
screen_width, screen_height = pyautogui.size()

# ------------------ Smoothing Settings ------------------
frameR = 80        # control rectangle size
alpha = 0.15       # ultra smooth filter
plocX, plocY = 0, 0
clocX, clocY = 0, 0

clicking = False
right_clicking = False
last_scroll_time = 0
scroll_delay = 0.3
last_screenshot_time = 0
screenshot_delay = 1  # seconds between screenshots

pTime = 0

# ------------------ Volume Control Setup ------------------
speakers = AudioUtilities.GetSpeakers()
interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
vol_range = volume.GetVolumeRange()
min_vol, max_vol = vol_range[0], vol_range[1]

# ------------------ Main Loop ------------------
while True:
    success, img = cap.read()
    if not success:
        continue
    img = cv2.flip(img, 1)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
    h, w, c = img.shape

    cv2.rectangle(img, (frameR, frameR), (w - frameR, h - frameR), (255, 0, 255), 2)

    if result.multi_hand_landmarks:
        for handLms in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)

            # ---------------- Finger Landmarks ----------------
            index_x = int(handLms.landmark[8].x * w)
            index_y = int(handLms.landmark[8].y * h)
            thumb_x = int(handLms.landmark[4].x * w)
            thumb_y = int(handLms.landmark[4].y * h)
            middle_x = int(handLms.landmark[12].x * w)
            middle_y = int(handLms.landmark[12].y * h)
            ring_x = int(handLms.landmark[16].x * w)
            ring_y = int(handLms.landmark[16].y * h)
            pinky_x = int(handLms.landmark[20].x * w)
            pinky_y = int(handLms.landmark[20].y * h)
            wrist_x = int(handLms.landmark[0].x * w)

            # ---------------- LEFT CLICK ----------------
            if math.hypot(index_x - thumb_x, index_y - thumb_y) < 35:
                if not clicking:
                    clicking = True
                    pyautogui.click()
            else:
                clicking = False

            # ---------------- RIGHT CLICK (3-Finger Pinch) ----------------
            middle_thumb_dist = math.hypot(middle_x - thumb_x, middle_y - thumb_y)
            if math.hypot(index_x - thumb_x, index_y - thumb_y) < 35 and middle_thumb_dist < 35:
                if not right_clicking:
                    right_clicking = True
                    pyautogui.rightClick()
            else:
                right_clicking = False

            # ---------------- SCROLL (4 Fingers Folded) ----------------
            index_folded = handLms.landmark[8].y > handLms.landmark[6].y
            middle_folded = handLms.landmark[12].y > handLms.landmark[10].y
            ring_folded = handLms.landmark[16].y > handLms.landmark[14].y
            pinky_folded = handLms.landmark[20].y > handLms.landmark[18].y
            four_folded = index_folded and middle_folded and ring_folded and pinky_folded

            current_time = time.time()
            if four_folded and (current_time - last_scroll_time > scroll_delay):
                avg_finger_x = (index_x + middle_x + ring_x + pinky_x) / 4
                if avg_finger_x > wrist_x:
                    pyautogui.scroll(100)  # Scroll UP
                else:
                    pyautogui.scroll(-100)  # Scroll DOWN
                last_scroll_time = current_time

            # ---------------- SCREENSHOT (3 Middle Fingers Raised) ----------------
            thumb_down = handLms.landmark[4].y > handLms.landmark[3].y
            pinky_down = handLms.landmark[20].y > handLms.landmark[19].y
            index_up = handLms.landmark[8].y < handLms.landmark[6].y
            middle_up = handLms.landmark[12].y < handLms.landmark[10].y
            ring_up = handLms.landmark[16].y < handLms.landmark[14].y

            if index_up and middle_up and ring_up and thumb_down and pinky_down:
                if current_time - last_screenshot_time > screenshot_delay:
                    filename = f"Screenshots/screenshot_{int(time.time())}.png"
                    pyautogui.screenshot(filename)
                    print(f"Screenshot saved: {filename}")
                    last_screenshot_time = current_time

            # ---------------- VOLUME CONTROL (Thumb + Index Distance) ----------------
            thumb_index_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
            vol = np.interp(thumb_index_dist, [20, 200], [min_vol, max_vol])
            volume.SetMasterVolumeLevel(vol, None)

            # ---------------- CURSOR MOVEMENT ----------------
            screen_x = np.interp(index_x, [frameR, w - frameR], [0, screen_width])
            screen_y = np.interp(index_y, [frameR, h - frameR], [0, screen_height])
            clocX = plocX + alpha * (screen_x - plocX)
            clocY = plocY + alpha * (screen_y - plocY)
            if abs(clocX - plocX) < 1:
                clocX = plocX
            if abs(clocY - plocY) < 1:
                clocY = plocY
            pyautogui.moveTo(clocX, clocY)
            plocX, plocY = clocX, clocY

            cv2.circle(img, (index_x, index_y), 8, (0, 255, 0), cv2.FILLED)

    # ---------------- FPS Counter ----------------
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

    cv2.imshow("Invisible Mouse - Ultra Smooth", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()