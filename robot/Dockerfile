FROM python:3.12.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --system --uid 10002 robot
# robot.py is the provided handout and is used unmodified.
COPY robot.py .
USER robot
ENTRYPOINT ["python", "robot.py"]
CMD ["--broker", "tcp://broker:1883"]
