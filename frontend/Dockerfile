# Ön yüz (SPA) üretim imajı: Vite derlemesi → nginx statik sunucu.
# API aynı alan adında Traefik arkasında (/api, /saglik, /docs); bu yüzden VITE_API_URL boş
# derlenir ve istekler göreli adrese gider (tenant = alt alan adı, kök alan aynı kalır).
FROM node:22-alpine AS derle
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=derle /src/dist /usr/share/nginx/html
EXPOSE 80
