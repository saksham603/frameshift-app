# ============================================================================
# File: README.md
# ============================================================================
# FrameShift - Visual Comparison Engine

A web application for detecting and analyzing visual changes in time-series images, built specifically for F1 race analysis.

## Features

- 🏎️ **F1 Tire Degradation Analysis**: Detect texture changes over race distance
- 📍 **Position Change Detection**: Track car movements and overtakes
- 🎯 **ROI Selection**: Focus on specific regions of interest
- 🔍 **Edge Detection**: Enhanced texture analysis for wear patterns
- 📝 **Text Filtering**: Ignore broadcast overlays and graphics
- 🖼️ **Background Removal**: Isolate subjects from busy backgrounds

## Project Structure

```
frameshift-app/
├── api/
│   └── main.py              # FastAPI backend
├── src/
│   ├── App.js              # React frontend (use artifact code)
│   └── index.js
├── public/
│   └── index.html
├── vercel.json             # Vercel configuration
├── requirements.txt        # Python dependencies
└── package.json           # Node.js dependencies
```

## Local Development

### Backend (Python FastAPI)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run FastAPI server
cd api
uvicorn main:app --reload --port 8000
```

### Frontend (React)

```bash
# Install Node dependencies
npm install

# Run React development server
npm start
```

The app will be available at `http://localhost:3000`

## Deployment to Vercel

### Prerequisites
- Vercel account (free tier works)
- Vercel CLI installed: `npm i -g vercel`

### Deploy Steps

1. **Install Vercel CLI**
```bash
npm install -g vercel
```

2. **Login to Vercel**
```bash
vercel login
```

3. **Deploy**
```bash
vercel
```

Follow the prompts:
- Set up and deploy? **Y**
- Which scope? (Select your account)
- Link to existing project? **N**
- Project name? **frameshift-app**
- Directory? **./** (root)
- Override settings? **N**

4. **Production Deploy**
```bash
vercel --prod
```

### Environment Variables (if needed)

In Vercel dashboard, add any environment variables:
- No special environment variables required for basic setup

## API Endpoints

### POST `/api/analyze`

Analyzes two images and returns detected changes.

**Request:**
- `image1` (file): First image (before)
- `image2` (file): Second image (after)
- `config` (JSON string):
  ```json
  {
    "use_roi": false,
    "remove_background": true,
    "use_edge_detection": true,
    "filter_text_regions": true,
    "sensitivity": 0.15
  }
  ```

**Response:**
```json
{
  "success": true,
  "changes_count": 5,
  "ssim_score": 0.856,
  "changes": [
    {
      "bbox": [100, 200, 50, 50],
      "area": 2500.0,
      "aspect_ratio": 1.0
    }
  ],
  "difference_map": "base64_encoded_image",
  "annotated_image": "base64_encoded_image"
}
```

## Configuration Options

- **ROI Selection**: Focus analysis on specific regions
- **Background Removal**: Remove distracting backgrounds using GrabCut
- **Edge Detection**: Enhanced texture analysis for wear patterns
- **Text Filtering**: Ignore text overlays and graphics
- **Sensitivity**: Threshold for change detection (0.05-0.30)

## Use Cases

### 🏎️ F1 Tire Wear Analysis
- Enable: Edge Detection + Background Removal
- Upload: Onboard camera footage from different laps
- Result: Detects texture changes indicating tire degradation

### 🎯 Overtaking Detection
- Enable: Background Removal + Text Filtering
- Upload: Track camera footage before/after overtake
- Result: Highlights position changes

### 📝 Broadcast Analysis
- Enable: Filter Text Regions
- Upload: TV broadcast frames
- Result: Ignores graphics, focuses on actual changes

## Tech Stack

- **Frontend**: React, TailwindCSS, Lucide Icons
- **Backend**: FastAPI (Python)
- **Image Processing**: OpenCV, scikit-image
- **Deployment**: Vercel (serverless)

## Troubleshooting

### Images not uploading?
- Check file size (max 10MB recommended)
- Ensure images are in supported format (JPG, PNG)

### Analysis taking too long?
- Reduce sensitivity value
- Disable background removal for faster processing
- Use smaller images (will be auto-resized to 1024px max)

### No changes detected?
- Increase sensitivity (lower value = more sensitive)
- Ensure images are from same camera angle
- Try enabling edge detection for texture changes

## License

MIT License - Free for personal and commercial use

## Credits

Built for F1 race analysis and general-purpose visual comparison tasks.