import cv2
import numpy as np
from typing import Tuple, Dict, Any

class ImagePreprocessor:
    """Модуль предобработки фотографий автомобилей с помощью OpenCV."""

    def __init__(self, target_size: int = 640):
        self.target_size = target_size

    def decode_image(self, image_bytes: bytes) -> np.ndarray:
        """Декодирует байты в BGR numpy массив."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Не удалось декодировать изображение. Неверный формат.")
        return img

    def apply_clahe(self, img_bgr: np.ndarray) -> np.ndarray:
        """Адаптивное выравнивание контраста в канале яркости LAB (CLAHE) для выявления мелких царапин."""
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def denoise(self, img_bgr: np.ndarray) -> np.ndarray:
        """Мягкая фильтрация шума матрицы камеры."""
        return cv2.GaussianBlur(img_bgr, (3, 3), 0)

    def letterbox_resize(self, img: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Ресайз с сохранением пропорций (letterbox padding) под размер модели (640x640)."""
        shape = img.shape[:2]  # [высота, ширина]
        r = min(self.target_size / shape[0], self.target_size / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw = (self.target_size - new_unpad[0]) / 2  # паддинг по ширине
        dh = (self.target_size - new_unpad[1]) / 2  # паддинг по высоте

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, r, (int(dw), int(dh))

    def process(self, image_bytes: bytes) -> Dict[str, Any]:
        raw_bgr = self.decode_image(image_bytes)
        enhanced = self.apply_clahe(raw_bgr)
        denoised = self.denoise(enhanced)
        input_tensor, ratio, padding = self.letterbox_resize(denoised)

        return {
            "original_bgr": raw_bgr,
            "processed_bgr": input_tensor,
            "original_shape": raw_bgr.shape,
            "scale_ratio": ratio,
            "padding": padding
        }
