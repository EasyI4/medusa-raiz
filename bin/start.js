const { spawn } = require("child_process")

const flask = spawn("gunicorn", [
  "--bind", "127.0.0.1:5001",
  "--workers", "1",
  "--threads", "4",
  "--timeout", "120",
  "app:app",
], {
  stdio: "inherit",
  env: {
    ...process.env,
    ASK_URL: process.env.ASK_URL || "http://127.0.0.1:5001/question/ask",
  },
})

const web = spawn("node", ["web/.output/server/index.mjs"], {
  stdio: "inherit",
  env: { ...process.env, HOST: "0.0.0.0", NITRO_HOST: "0.0.0.0", API_ORIGIN: "http://127.0.0.1:5001" },
})

function stop() {
  flask.kill()
  web.kill()
  process.exit()
}

flask.on("exit", (code) => {
  web.kill()
  process.exit(code || 1)
})
web.on("exit", (code) => {
  flask.kill()
  process.exit(code || 1)
})
process.on("SIGTERM", stop)
process.on("SIGINT", stop)
