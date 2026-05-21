FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY package.json ./
RUN npm install

# 复制代码
COPY . .

# 启动开发服务器
CMD ["npm", "run", "dev", "--", "--host"]
