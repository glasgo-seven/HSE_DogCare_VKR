import cv2, numpy as np, joblib, os
from ultralytics import YOLO
from sklearn.ensemble import RandomForestClassifier

class CalmnessML:
	def __init__(self, model_path="calmness_model.pkl"):
		self.prev_gray = None
		self.buf = []
		self.buf_len = 12  # ~0.4с при 30fps
		self.state = "calm"
		self.stab = 0

		if os.path.exists(model_path):
			self.clf = joblib.load(model_path)
			self.use_ml = True
		else:
			self.use_ml = False
			self.thr = 1.5  # fallback порог
			print("⚠️ Модель не найдена. Использую эвристический порог.")

	def _features(self, crop):
		if crop is None or crop.size == 0:
			return None
		small = cv2.resize(crop, None, fx=0.5, fy=0.5)
		if small is None or small.size == 0:
			return None
		gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
		h, w = gray.shape
		feats = []
		if self.prev_gray is not None:
			flow = cv2.calcOpticalFlowFarneback(self.prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
			mag = cv2.magnitude(flow[...,0], flow[...,1])
			feats = [
				np.mean(mag),
				np.std(mag),
				np.percentile(mag, 90),
				h / w  # соотношение сторон кропа
			]
		self.prev_gray = gray
		return feats if len(feats)==4 else None

	def predict(self, crop):
		f = self._features(crop)
		if f is None: return "init"

		self.buf.append(f)
		if len(self.buf) > self.buf_len: self.buf.pop(0)

		if len(self.buf) < 5: return "warmup"

		avg = np.mean(self.buf, axis=0).reshape(1,-1)
		raw = "active" if (self.clf.predict(avg)[0]==1 if self.use_ml else avg[0][0]>self.thr) else "calm"

		# гистерезис (защита от мерцания)
		if raw == self.state: self.stab = 0
		else:
			self.stab += 1
			if self.stab >= 4: self.state = raw; self.stab = 0
		return self.state

def train_model(source):
	"""
	Нужно 30-50 кадров каждого вида активности
	"""
	detector = CalmnessML()  # создаёт объект без модели
	X, y = [], []
	cap = cv2.VideoCapture(source)
	print("Нажмите 'c' когда собака спокойна, 'a' когда активна, 'q' для сохранения")

	while cap.isOpened():
		ret, frame = cap.read()
		if not ret: break
		# возьмём первый детектированный кроп
		boxes = YOLO("yolov8n.pt")(frame, conf=0.3, verbose=False)[0].boxes.xyxy
		if len(boxes)==0: continue
		x1,y1,x2,y2 = map(int, boxes[0])
		crop = frame[y1:y2, x1:x2]

		f = detector._features(crop)
		if f is not None:
			cv2.imshow("Collect", cv2.resize(crop, (320,320)))
			key = cv2.waitKey(1) & 0xFF
			if key == ord("c"): X.append(f); y.append(0); print("Calm saved")
			elif key == ord("a"): X.append(f); y.append(1); print("Active saved")
			elif key == ord("q"): break

	cap.release(); cv2.destroyAllWindows()

	if len(X) > 20:
		clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
		clf.fit(X, y)
		joblib.dump(clf, "calmness_model.pkl")
		print(f"Model saved. Accuracy on train: {clf.score(X,y):.2f}")
	else:
		print("Need >20 samples per class")

def get_activity(frame):
	detector = YOLO('yolov8n.pt')
	analyzer = CalmnessML('calmness_model.pkl')

	results = detector(frame, conf=0.25, verbose=False)[0]
	dog_mask = results.boxes.cls == 16
	boxes = results.boxes.xyxy[dog_mask].cpu().numpy()

	for box in boxes:
		x1, y1, x2, y2 = map(int, box)
		crop = frame[y1:y2, x1:x2]
		if crop.size == 0: continue

		state = analyzer.predict(crop)
		color = (0, 255, 0) if state == "calm" else (0, 0, 255)
		cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
		cv2.putText(frame, state, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

if __name__ == '__main__':
	train_model('')
