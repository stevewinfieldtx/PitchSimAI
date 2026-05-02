# Build stage
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build


# Serve stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE ${PORT:-3000}

CMD sh -c "envsubst '\$PORT \$BACKEND_URL' < /etc/nginx/conf.d/default.conf > /tmp/default.conf && mv /tmp/default.conf /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"