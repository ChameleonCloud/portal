FROM node:lts as deps

COPY package.json package.json
COPY yarn.lock yarn.lock
RUN yarn install

FROM node:lts

COPY --from=deps node_modules /project/node_modules

COPY . /project
WORKDIR /project

RUN yarn build --production
