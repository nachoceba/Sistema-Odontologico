# Etapas (spec demo-packaging): dev = servidor de Vite con recarga (docker compose up),
# build = SPA construida con VITE_API_URL fijada, demo = nginx con solo los archivos estaticos.
FROM node:22-alpine AS dev

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM dev AS build

# URL publica de la API para el navegador; es la unica variable que entra al bundle.
ARG VITE_API_URL
RUN test -n "$VITE_API_URL" || { echo "Falta el argumento de build VITE_API_URL (URL de la API)" >&2; exit 1; }
ENV VITE_API_URL=$VITE_API_URL
# El chequeo del bundle hace fallar el build si aparece un nombre o patron de secreto.
RUN npm run build && npm run check:bundle

FROM nginx:alpine AS demo

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
