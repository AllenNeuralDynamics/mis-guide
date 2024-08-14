import logging
import os
import cv2
import numpy as np
from datetime import datetime

# Set logger name
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
# Set the logging level for PyQt5.uic.uiparser/properties to WARNING, to ignore DEBUG messages
logging.getLogger("PyQt5.uic.uiparser").setLevel(logging.WARNING)
logging.getLogger("PyQt5.uic.properties").setLevel(logging.WARNING)

if logger.getEffectiveLevel() == logging.DEBUG:
    package_dir = os.path.dirname(os.path.abspath(__file__))
    debug_dir = os.path.join(os.path.dirname(package_dir), "debug_images")
    os.makedirs(debug_dir, exist_ok=True)

class ProbeFineTipDetector:
    """Class for detecting the fine tip of the probe in an image."""

    @classmethod
    def _preprocess_image(cls, img):
        """Preprocess the image for tip detection."""
        img = cv2.GaussianBlur(img, (7, 7), 0)
        sharpened_image = cv2.Laplacian(img, cv2.CV_64F)
        sharpened_image = np.uint8(np.absolute(sharpened_image))
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return img

    @classmethod
    def _is_valid(cls, img):
        """Check if the image is valid for tip detection.
        Returns:
            bool: True if the image is valid, False otherwise.
        """
        height, width = img.shape[:2]
        boundary_img = np.zeros_like(img)
        cv2.rectangle(boundary_img, (0, 0), (width - 1, height - 1), 255, 1)
        and_result = cv2.bitwise_and(cv2.bitwise_not(img), boundary_img)
        contours_boundary, _ = cv2.findContours(
            and_result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if len(contours_boundary) >= 2:
            logger.debug(
                f"get_probe_precise_tip fail. N of contours_boundary :{len(contours_boundary)}"
            )
            return False

        boundary_img = np.zeros_like(img)
        boundary_img[0, 0] = 255
        boundary_img[width - 1, 0] = 255
        boundary_img[0, height - 1] = 255
        boundary_img[width - 1, height - 1] = 255
        and_result = cv2.bitwise_and(and_result, boundary_img)
        contours_boundary, _ = cv2.findContours(
            and_result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if len(contours_boundary) >= 2:
            logger.debug(
                f"get_probe_precise_tip fail. No detection of tip :{len(contours_boundary)}"
            )
            return False
        return True

    @classmethod
    def _detect_closest_centroid(cls, img, tip, offset_x, offset_y, direction):
        """Detect the closest centroid to the tip.

        Returns:
            tuple: Coordinates of the closest centroid.
        """
        cx, cy = tip[0], tip[1]
        closest_centroid = (cx, cy)
        min_distance = float("inf")

        harris_corners = cv2.cornerHarris(img, blockSize=7, ksize=5, k=0.1)
        threshold = 0.3 * harris_corners.max()

        corner_marks = np.zeros_like(img)
        corner_marks[harris_corners > threshold] = 255
        contours, _ = cv2.findContours(
            corner_marks, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            contour_tip = cls._get_direction_tip(contour, direction)
            tip_x, tip_y = contour_tip[0] + offset_x, contour_tip[1] + offset_y
            distance = np.sqrt((tip_x - cx) ** 2 + (tip_y - cy) ** 2)
            if distance < min_distance:
                min_distance = distance
                closest_centroid = (tip_x, tip_y)

        return closest_centroid

    @classmethod
    def _get_direction_tip(cls, contour, direction):
        """Get the tip coordinates based on the direction.

        Args:
            contour (numpy.ndarray): Contour of the tip.

        Returns:
            tuple: Coordinates of the tip based on the direction.
        """
        tip = (0, 0)
        if direction == "S":
            tip = max(contour, key=lambda point: point[0][1])[0]
        elif direction == "N":
            tip = min(contour, key=lambda point: point[0][1])[0]
        elif direction == "E":
            tip = max(contour, key=lambda point: point[0][0])[0]
        elif direction == "W":
            tip = min(contour, key=lambda point: point[0][0])[0]
        elif direction == "NE":
            tip = min(contour, key=lambda point: point[0][1] - point[0][0])[0]
        elif direction == "NW":
            tip = min(contour, key=lambda point: point[0][1] + point[0][0])[0]
        elif direction == "SE":
            tip = max(contour, key=lambda point: point[0][1] + point[0][0])[0]
        elif direction == "SW":
            tip = max(contour, key=lambda point: point[0][1] - point[0][0])[0]

        return tip

    @classmethod
    def get_precise_tip(cls, img, tip, offset_x=0, offset_y=0, direction="S", cam_name="cam"):
        """Get the precise tip coordinates from the image."""
        if logger.getEffectiveLevel() == logging.DEBUG:
            save_path = os.path.join(debug_dir, f"{cam_name}_tip.jpg")
            cv2.imwrite(save_path, img)

        img = cls._preprocess_image(img)
        if not cls._is_valid(img):
            logger.debug("Boundary check failed.")
            return False, tip

        precise_tip = cls._detect_closest_centroid(img, tip, offset_x, offset_y, direction)

        return True, precise_tip
