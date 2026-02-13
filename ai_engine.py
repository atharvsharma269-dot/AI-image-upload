import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import hashlib
import time


# ------------------------------
# Image Preprocessing
# ------------------------------
def preprocess_image(image_path):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Invalid image path or unsupported format.")

    image = cv2.resize(image, (500, 500))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray


# ------------------------------
# Fraud Detection (Same Image Check)
# ------------------------------
def compute_image_hash(image_path):
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


# ------------------------------
# Core Comparison Logic
# ------------------------------
def analyze_images(before_path, after_path):
    start_time = time.time()

    # Fraud Detection
    if compute_image_hash(before_path) == compute_image_hash(after_path):
        return {
            "similarity_score": 1.0,
            "quality_score": 0,
            "completion_status": "Fraud Detected - Same Image Uploaded",
            "processing_time_ms": 0
        }

    before = preprocess_image(before_path)
    after = preprocess_image(after_path)

    # Structural Similarity
    similarity_score, diff = ssim(before, after, full=True)
    diff = (diff * 255).astype("uint8")

    # Improvement Score Calculation
    quality_score = round((1 - similarity_score) * 100, 2)

    # Completion Threshold
    if quality_score > 20:
        status = "Completed"
    else:
        status = "Incomplete"

    # Save heatmap for visualization
    heatmap = cv2.applyColorMap(diff, cv2.COLORMAP_JET)
    cv2.imwrite("difference_heatmap.jpg", heatmap)

    processing_time = round((time.time() - start_time) * 1000, 2)

    return {
       
    "similarity_score": float(round(similarity_score, 4)),
    "quality_score": float(quality_score),
    "completion_status": status,
    "processing_time_ms": float(processing_time)
    

    }


# ------------------------------
# Local Testing
# ------------------------------
if __name__ == "__main__":
    result = analyze_images("before.jpg", "after.jpg")
    print(result)
