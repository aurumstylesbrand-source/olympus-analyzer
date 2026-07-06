FROM node:20-alpine
WORKDIR /app

# No npm dependencies — copy the source directly.
# Must include olympus_console.html (served at /) and olympus_standard.md (read by server.js).
COPY package.json server.js analyze.js judge_rubric.md olympus_standard.md olympus_console.html ./

EXPOSE 8787
CMD ["node", "server.js"]
