FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000
ARG VITE_TELEGRAM_BOT_URL=https://t.me/DecoSmartBot
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_TELEGRAM_BOT_URL=$VITE_TELEGRAM_BOT_URL
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
