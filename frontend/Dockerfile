# Build stage
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
# Cloud Run node URLs baked at build time:
ARG VITE_NODE_TS=http://localhost:8001
ARG VITE_NODE_OD=http://localhost:8002
ENV VITE_NODE_TS=$VITE_NODE_TS VITE_NODE_OD=$VITE_NODE_OD
RUN npm run build

# Serve stage
FROM node:22-slim
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "serve -s dist -l ${PORT}"]
