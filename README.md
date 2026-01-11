# PyImgScan GUI

A user-friendly desktop application for scanning and analyzing documents from images.

## Features

- **Advanced Document Cropping:** A powerful system to straighten and isolate documents from a photo.
  - **Automatic Mode:** A sophisticated two-stage algorithm that first detects the outer border of the photo/scan and then the inner document.
  - **Manual Mode:** An interactive tool that allows you to drag the corners of a bounding box to precisely define the crop area. It's perfect for fine-tuning the automatic detection or for images where automatic detection is difficult.

- **Advanced Glare Removal:** A suite of tools to remove glare and specular highlights from your images.
  - **Single-Image Methods:**
    - **Inpainting:** "Fills in" glare spots by sampling surrounding pixels. Best for localized, well-defined glare.
    - **Morphological:** Uses image processing to reduce specular highlights.
    - **Adaptive:** A hybrid method that combines filtering and inpainting for robust results on mixed glare types.
  - **Multi-Photo Blending:** A professional technique that combines four images taken from different angles (top, bottom, left, right). It intelligently blends the non-glare regions from each photo to produce a single, glare-free image.

- **Compression Analysis:** An integrated tool to *generate and* analyze the effects of JPEG compression. It allows you to:
    - *Generate a compressed image to* a target file size (30KB, 100KB, 500KB, 1MB) or run a full analysis *across multiple target sizes*.
    - View the visually compressed image in the main window (for single-target analysis).
    - Access a detailed report with objective quality metrics (PSNR, SSIM, MSE).
    - Visualize the quality-size trade-off with a rate-distortion plot.
    - Get subjective analysis and recommendations for optimal compression.

- **Undo/Redo History:** Easily revert or re-apply changes using dedicated "Undo" and "Redo" buttons.
- **Change Picture:** Load a new image to work on without restarting the application.
- **Save Your Work:** Save the final edited image to your computer.

## Requirements

- Python 3.x
- The Python packages listed in `requirements-gui.txt`.

## How to Run

1.  **Install Dependencies:**
    Before running the application, make sure you have all the necessary packages installed. If you are in a virtual environment, make sure it's activated.

    ```bash
    pip install -r requirements-gui.txt
    ```

2.  **Run the Application:**

    ```bash
    python3 gui.py
    ```

## How to Use

1.  **Select an Image:**
    - On the welcome screen, click "Select Image" to choose a document image from your computer.

2.  **Edit the Image:**
    - The image will appear in the main editor window.
    - Use the tools in the left sidebar to process the image:
        - **Detect & Crop:** This button has two modes:
            - **Auto Crop (Stage 1 & 2):** Click once to detect the photo's outer border. Click again to detect the inner document.
            - **Manual Crop:** Opens a new window where you can drag the four corners of the crop selection. Click "Apply Crop" when finished.
        - **Remove Glare:** Opens a dialog with several glare removal options:
            - **Single-Image Methods:** Choose between "Inpainting", "Morphological", or "Adaptive". Adjust the intensity with the slider and click "Apply".
            - **Multi-Photo Blending:** Click "Load Photos & Blend" to open a new dialog. Load the four required images (top, bottom, left, right) and then click "Apply" to start the blending process.
        - **Analyze Compression:** Opens a pop-up where you can select a target file size for analysis (e.g., 30KB, 100KB) or click "Run All & Plot" for a comprehensive analysis.
            - For single-target analysis, the compressed image will be displayed in the main window.
            - After any analysis, the "Show Analysis Report" button will become active to view the detailed report and plot.
        - **Change Picture:** Load a new image into the editor.

    - Use the buttons at the bottom to manage your workflow:
        - **Undo:** Reverts the last action.
        - **Redo:** Re-applies the last undone action.
        - **Save Image:** Saves the currently displayed image to a file.
