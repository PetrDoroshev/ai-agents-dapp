import cv2
import asyncio
import requests
import variables
import json

from ultralytics import YOLO

async def execute_deepseek(input_path: str, output_path: str):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {variables.DEEPSEEK_API_KEY}"
    }

    try:
        new_out_path = f"{output_path}.txt"
        print("Executing deepseek")
        print(new_out_path)

        f = open(input_path, 'r', encoding="utf-8")
        text_to_send = f.read()
        f.close()

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {variables.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "deepseek/deepseek-r1-0528:free",
                "messages": [
                {
                    "role": "user",
                    "content": text_to_send
                }
                ],
                
            })
        )

        output_text = ""

        if response.status_code == 200:
            result = response.json()
            output_text = result['choices'][0]['message']['content']
        else:
            print("Request failed, error code:", response.status_code)
            raise ValueError("Deepseek failed to fetch")

        f = open(new_out_path, 'w', encoding="utf-8")
        f.write(output_text)
        f.close()

        return new_out_path
    except Exception as e:
        print(f"Deepseek error: {e}")
        return None

async def execute_object_detection(input_path: str, output_path: str):
    """Execute object detection model (simplified example)"""
    try:
        print("Executing object detection")
        new_out_path = f"{output_path}.png"
        print(new_out_path)

        img = cv2.imread(input_path)
        model = YOLO('yolov8n.pt')
        results = model(img)

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cls_id = int(box.cls[0])
            conf = box.conf[0]
            label = results[0].names[cls_id]

            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(img, f"{label} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

        cv2.imwrite(new_out_path, img)
        print("object detection executed")
        return new_out_path
    except Exception as e:
        print(f"Object detection error: {e}")
        return None
