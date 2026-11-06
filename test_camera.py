"""Grab one frame from the Viam camera and save it as camera_test.png.
Also prints every image source the camera returns, so you can see the color stream's name.
Run from the project folder:  python test_camera.py"""
import asyncio
import cv2
from viam.components.camera import Camera
import config
from common import connect, grab_frame


async def main():
    robot = await connect()
    try:
        cam = Camera.from_robot(robot, config.CAM_NAME)
        if hasattr(cam, "get_images"):
            images, _ = await cam.get_images()
            for i in images:
                print("source:", getattr(i, "name", getattr(i, "source_name", "?")),
                      "| mime:", getattr(i, "mime_type", "?"))
        frame = await grab_frame(cam)
        cv2.imwrite("camera_test.png", frame)
        print(f"Saved camera_test.png ({frame.shape[1]}x{frame.shape[0]}). Open it and check the colors look right.")
    finally:
        await robot.close()


asyncio.run(main())
