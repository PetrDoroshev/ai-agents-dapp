import cv2
import asyncio

async def execute_style_transfer(input_path: str, output_path: str):
    try:
        new_out_path = f"{output_path}.png"
        print("Executing style transfer")
        print(new_out_path)
        img = cv2.imread(input_path)
        await asyncio.sleep(10)

        cv2.imwrite(new_out_path, img)
        print("Style transfer executed")
        return new_out_path
    except Exception as e:
        print(f"Style transfer error: {e}")
        return None

async def execute_object_detection(input_path: str, output_path: str):
    """Execute object detection model (simplified example)"""
    try:
        print("Executing object detection")
        new_out_path = f"{output_path}.png"
        print(new_out_path)
        img = cv2.imread(input_path)
        await asyncio.sleep(5)

        cv2.imwrite(new_out_path, img)
        print("object detection executed")
        return new_out_path
    except Exception as e:
        print(f"Object detection error: {e}")
        return None