import asyncio, json
from viam.robot.client import RobotClient
from viam.proto.component.arm import JointPositions
import config
from vision import viam_to_bgr


async def connect():
    opts = RobotClient.Options.with_api_key(
        api_key=config.API_KEY, api_key_id=config.API_KEY_ID
    )
    return await RobotClient.at_address(config.VIAM_ADDRESS, opts)


async def grab_frame(cam):
    """Return one COLOR frame as an OpenCV BGR array.
    Newer viam-sdk: cam.get_images() -> (list of named images, metadata). A RealSense returns
    color and depth, so we pick the color one. Falls back to cam.get_image() on older SDKs."""
    if hasattr(cam, "get_images"):
        try:
            images, _ = await cam.get_images(filter_source_names=[config.CAM_COLOR_SOURCE])
        except Exception:
            images = []
        if not images:
            images, _ = await cam.get_images()
        names = [getattr(i, "name", getattr(i, "source_name", "?")) for i in images]
        img = _pick_color(images)
        if img is None:
            raise RuntimeError(f"No color image found. Sources returned: {names}. "
                               f"Set CAM_COLOR_SOURCE in config.py to the right name.")
        return viam_to_bgr(img)
    return viam_to_bgr(await cam.get_image())


def _pick_color(images):
    def name(i):
        return str(getattr(i, "name", getattr(i, "source_name", ""))).lower()

    def mime(i):
        return str(getattr(i, "mime_type", "")).lower()

    for i in images:                       # 1) explicit color name
        if "color" in name(i) or "rgb" in name(i):
            return i
    for i in images:                       # 2) anything that is a normal jpeg/png, not depth
        if ("jpeg" in mime(i) or "png" in mime(i)) and "depth" not in name(i) and "dep" not in mime(i):
            return i
    return images[0] if images else None


def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def load_json(path):
    with open(path) as f:
        return json.load(f)


async def move_to_scan_pose(arm):
    joints = load_json(config.SCAN_POSE_FILE)["joints"]
    await arm.move_to_joint_positions(JointPositions(values=joints))
    await asyncio.sleep(1.5)  # let vibration settle so the image isn't blurry
