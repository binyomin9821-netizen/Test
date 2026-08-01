FROM python:3.12-slim

WORKDIR /app

# tesseract-ocr: the OCR engine pytesseract calls into. Not a Python
# package -- has to be installed as a system binary.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "run.py"]
