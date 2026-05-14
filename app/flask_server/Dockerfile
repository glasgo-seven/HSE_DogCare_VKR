FROM python:3.11-slim
WORKDIR /app

# Минимальные системные библиотеки для OpenCV headless / libGL (без X11)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# ultralytics тянет opencv-python; в конце оставляем только headless (cv2 без X11)
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --force-reinstall "opencv-python-headless>=4.8.0"
COPY . .
CMD ["python", "app.py"]