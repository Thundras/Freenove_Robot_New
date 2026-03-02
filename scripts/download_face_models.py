import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS = {
    "face_detection_yunet.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
}

TARGET_DIR = r"c:\Users\iphar\Documents\Anitgravity\Freenove_Robot\freenove_robot_new\brain\models"

def download_models():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        logger.info(f"Created directory: {TARGET_DIR}")

    for name, url in MODELS.items():
        path = os.path.join(TARGET_DIR, name)
        if os.path.exists(path):
            logger.info(f"Model {name} already exists. Skipping.")
            continue

        logger.info(f"Downloading {name} from {url}...")
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Successfully downloaded {name}")
        except Exception as e:
            logger.error(f"Failed to download {name}: {e}")

if __name__ == "__main__":
    download_models()
