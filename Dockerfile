FROM node:20-alpine
WORKDIR /app

# No npm dependencies — copy the source directly.
COPY package.json server.js analyze.js judge_rubric.md ./

EXPOSE 8787
CMD ["node", "server.js"]
