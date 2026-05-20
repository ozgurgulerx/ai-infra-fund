ARG BASE_IMAGE=node:22-alpine

FROM ${BASE_IMAGE} AS deps

WORKDIR /app

COPY apps/web/package.json /app/package.json
COPY apps/web/package-lock.json /app/package-lock.json
RUN npm ci

FROM ${BASE_IMAGE} AS build

WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

COPY --from=deps /app/node_modules /app/node_modules
COPY apps/web /app
COPY docs/mock_data /app/docs/mock_data
RUN npm run build

FROM ${BASE_IMAGE} AS runtime

WORKDIR /app

ENV NODE_ENV=production

COPY --from=build /app/.next /app/.next
COPY --from=build /app/package.json /app/package.json
COPY --from=build /app/package-lock.json /app/package-lock.json
COPY --from=build /app/node_modules /app/node_modules
COPY --from=build /app/next.config.mjs /app/next.config.mjs

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
