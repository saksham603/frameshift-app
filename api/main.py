# api/main.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import base64
import json
from io import BytesIO
from PIL import Image

app = FastAPI()

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def decode_image(file_bytes):
    """Convert uploaded file to OpenCV image"""
    img = Image.open(BytesIO(file_bytes))
    img_array = np.array(img)
    if len(img_array.shape) == 2:  # Grayscale
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    elif img_array.shape[2] == 4:  # RGBA
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    return img_array

def encode_image(img):
    """Convert OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.png', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64

def remove_background_grabcut(img):
    """Remove background using GrabCut"""
    try:
        mask = np.zeros(img.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        h, w = img.shape[:2]
        rect = (int(w*0.1), int(h*0.1), int(w*0.8), int(h*0.8))
        
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        result = img * mask2[:, :, np.newaxis]
        return result, mask2
    except:
        return img, np.ones(img.shape[:2], np.uint8)

def remove_background_simple(img):
    """Simple background removal"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 30, 50])
    upper = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    result = cv2.bitwise_and(img, img, mask=mask)
    return result, mask

def align_images(img1, img2):
    """Align images using ORB features"""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)
    
    if des1 is None or des2 is None:
        return img1, gray1
    
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(des1, des2), key=lambda x: x.distance)
    
    if len(matches) > 10:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)
        H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC)
        
        h, w = img2.shape[:2]
        img1_aligned = cv2.warpPerspective(img1, H, (w, h))
        gray1_aligned = cv2.cvtColor(img1_aligned, cv2.COLOR_BGR2GRAY)
        return img1_aligned, gray1_aligned
    
    return img1, gray1

def compute_difference(gray1, gray2, use_edge_detection=False):
    """Compute difference map between images"""
    pixel_diff = cv2.absdiff(gray1, gray2).astype(float) / 255.0
    ssim_score, ssim_map = ssim(gray1, gray2, full=True)
    ssim_diff = 1 - ssim_map
    
    if use_edge_detection:
        edges1 = cv2.Canny(gray1, 50, 150)
        edges2 = cv2.Canny(gray2, 50, 150)
        edge_diff = cv2.absdiff(edges1, edges2).astype(float) / 255.0
        
        kernel = np.ones((15, 15), np.float32) / 225
        edge_density1 = cv2.filter2D(edges1.astype(float) / 255.0, -1, kernel)
        edge_density2 = cv2.filter2D(edges2.astype(float) / 255.0, -1, kernel)
        density_diff = np.abs(edge_density1 - edge_density2)
        
        difference_map = (0.2 * pixel_diff + 0.2 * ssim_diff + 
                         0.3 * edge_diff + 0.3 * density_diff)
    else:
        difference_map = (pixel_diff + ssim_diff) / 2
    
    return difference_map, ssim_score

def is_text_region(change):
    """Detect if region is likely text"""
    area = change['area']
    aspect_ratio = change['aspect_ratio']
    is_elongated = aspect_ratio > 2.5 or aspect_ratio < 0.4
    is_small_medium = 100 < area < 5000
    return is_elongated and is_small_medium

def find_changes(difference_map, sensitivity, filter_text=False):
    """Find changed regions"""
    binary = (difference_map > sensitivity).astype(np.uint8) * 255
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    changes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 100:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            change = {
                'bbox': [int(x), int(y), int(w), int(h)],
                'area': float(area),
                'aspect_ratio': float(aspect_ratio)
            }
            
            if filter_text and is_text_region(change):
                continue
            
            changes.append(change)
    
    changes.sort(key=lambda c: c['area'], reverse=True)
    return changes, binary

def create_visualizations(img2, difference_map, changes):
    """Create result visualizations"""
    # Difference map colored
    diff_colored = cv2.applyColorMap((difference_map * 255).astype(np.uint8), cv2.COLORMAP_JET)
    
    # Annotated image
    result = img2.copy()
    for i, change in enumerate(changes[:10]):
        x, y, w, h = change['bbox']
        color = (0, 0, 255) if i == 0 else (0, 255, 0)
        cv2.rectangle(result, (x, y), (x+w, y+h), color, 2)
        cv2.putText(result, f"#{i+1}", (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return diff_colored, result

@app.post("/api/analyze")
async def analyze_images(
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    config: str = Form(...)
):
    try:
        # Parse configuration
        config_dict = json.loads(config)
        
        # Load images
        img1_bytes = await image1.read()
        img2_bytes = await image2.read()
        
        img1 = decode_image(img1_bytes)
        img2 = decode_image(img2_bytes)
        
        # Resize if too large
        max_dim = 1024
        h1, w1 = img1.shape[:2]
        if max(h1, w1) > max_dim:
            scale = max_dim / max(h1, w1)
            img1 = cv2.resize(img1, None, fx=scale, fy=scale)
            img2 = cv2.resize(img2, None, fx=scale, fy=scale)
        
        # Background removal
        if config_dict.get('remove_background', False):
            try:
                img1, _ = remove_background_grabcut(img1)
                img2, _ = remove_background_grabcut(img2)
            except:
                img1, _ = remove_background_simple(img1)
                img2, _ = remove_background_simple(img2)
        
        # Align images
        img1_aligned, gray1_aligned = align_images(img1, img2)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Compute differences
        difference_map, ssim_score = compute_difference(
            gray1_aligned, 
            gray2, 
            config_dict.get('use_edge_detection', False)
        )
        
        # Find changes
        changes, binary = find_changes(
            difference_map,
            config_dict.get('sensitivity', 0.15),
            config_dict.get('filter_text_regions', False)
        )
        
        # Create visualizations
        diff_colored, annotated = create_visualizations(img2, difference_map, changes)
        
        # Encode results
        diff_base64 = encode_image(diff_colored)
        annotated_base64 = encode_image(annotated)
        
        return JSONResponse({
            "success": True,
            "changes_count": len(changes),
            "ssim_score": float(ssim_score),
            "changes": changes[:10],
            "difference_map": diff_base64,
            "annotated_image": annotated_base64
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/")
async def root():
    return {"message": "FrameShift API v1.1", "status": "ready"}

# For Vercel serverless function
handler = app