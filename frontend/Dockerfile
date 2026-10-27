# ---- dependencies (cached on the lockfile) ----
FROM node:24.21.0-alpine3.24 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---- lint + unit tests: `docker compose ... run --rm frontend-unit` ----
FROM deps AS test
COPY . .
# vite writes a transient bundled config and a cache next to the project.
RUN chown -R node:node /app
USER node
# Lint first: it enforces the folder dependency rules (see eslint.config.js).
CMD ["sh", "-c", "npm run lint && npx vitest run"]

# ---- production bundle (type-checked) ----
FROM deps AS build
COPY . .
RUN npm run build

# ---- static server: nginx, unprivileged (uid 101, port 8080) ----
FROM nginxinc/nginx-unprivileged:1.30.4-alpine3.24 AS web
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
