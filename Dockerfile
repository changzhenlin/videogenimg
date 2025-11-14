FROM python:3.11-slim

# 设置非交互式安装模式
ENV DEBIAN_FRONTEND=noninteractive

# 安装ffmpeg和必要的系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY auto_thumbnail.py .

# 创建必要的目录
RUN mkdir -p /videos /tmp/thumbnails

# 设置卷挂载点，用于连接NAS上的视频文件
VOLUME ["/videos"]

# 暴露Flask服务端口
EXPOSE 5000

# 设置默认命令 - 运行Web服务
CMD ["python", "auto_thumbnail.py"]

