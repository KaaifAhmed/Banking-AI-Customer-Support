/**
 * WhatsApp Service — small HTTP API, not a queue consumer.
 * Outbound: POST /whatsapp/send, called directly by the AI Worker Pool
 *   and Background Worker (via shared/whatsapp_client.py).
 * Inbound: forwards a lightweight payload (phone, text, media reference —
 *   never raw file bytes) to Main Service's /api/whatsapp/inbound.
 *
 * Pre-authenticate before the demo: run this once ahead of time, scan the
 * QR code, and the ./auth session folder keeps it logged in — don't scan
 * live during judging.
 */
const express = require("express");
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys");

const app = express();
app.use(express.json());

const MAIN_SERVICE_URL = process.env.MAIN_SERVICE_URL || "http://main-service:8000";
let sock;

async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("./auth");
  sock = makeWASocket({ auth: state, printQRInTerminal: true });
  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect } = update;
    if (connection === "close") {
      const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log("WhatsApp connection closed, reconnecting:", shouldReconnect);
      if (shouldReconnect) startWhatsApp();
    } else if (connection === "open") {
      console.log("WhatsApp connected");
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue;
      const phone = msg.key.remoteJid?.split("@")[0];
      const text = msg.message.conversation || msg.message.extendedTextMessage?.text || "";
      const mediaRef = msg.key.id; // reference only — worker fetches full media when it processes the job

      try {
        await fetch(`${MAIN_SERVICE_URL}/api/whatsapp/inbound`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, text, media_ref: mediaRef }),
        });
      } catch (err) {
        console.error("Failed to forward inbound message:", err);
      }
    }
  });
}

app.post("/whatsapp/send", async (req, res) => {
  const { phone, text } = req.body;
  try {
    await sock.sendMessage(`${phone}@s.whatsapp.net`, { text });
    res.json({ success: true, data: { sent: true }, error: null });
  } catch (err) {
    res.status(500).json({ success: false, data: null, error: { code: "send_failed", message: err.message } });
  }
});

app.get("/health", (req, res) => {
  res.json({ success: true, data: { status: "ok" }, error: null });
});

startWhatsApp();
app.listen(3001, () => console.log("WhatsApp Service listening on :3001"));
