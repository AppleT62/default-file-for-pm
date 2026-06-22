module.exports = {
  apps: [
    {
      name: "hermes-agent",
      script: "venv/bin/python3",
      args: "-m src.main",
      cwd: __dirname,
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      watch: false,
      out_file: "./logs/out.log",
      error_file: "./logs/error.log",
      time: true,
    },
  ],
};
