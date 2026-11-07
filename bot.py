"""Antarmuka Telegram A1 (SIMULASI). Mode webhook (Render free) atau long polling (lokal).
Tidak ada pesan yang dikirim ke pihak luar: draf hanya tampil di chat pengguna untuk disetujui;
'Setujui' cuma menandai status. Setiap chat punya data terpisah."""
import asyncio
import logging
import os
import re

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

load_dotenv()
import core  # noqa: E402  (setelah load_dotenv agar env terbaca)

logging.basicConfig(level=logging.INFO)
ADMIN = int(os.getenv("ADMIN_CHAT_ID")) if os.getenv("ADMIN_CHAT_ID") else None  # kosongkan untuk demo publik
SIM = "\n\n(SIMULASI TES, bukan informasi resmi MSI/awards. Jangan isi data nyata.)"


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Saya asisten layanan awards (SIMULASI). Tanyakan seputar pendaftaran, sponsor, atau wawancara.\n\n"
        "Perintah:\n/prospek Nama | email | telepon | minat  (pakai - jika kosong)\n"
        "/jumlah  jumlah prospek unik di chat ini\n/draf  draf menunggu persetujuan\n\n"
        "Catatan: data tiap chat terpisah dan bisa reset kapan saja. Tidak ada pesan nyata yang dikirim." + SIM)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.message.text
    res = await asyncio.to_thread(core.answer, q, None, update.effective_chat.id)
    msg = res["jawaban"]
    msg += "\n\nSumber: " + (", ".join(res["kb_dirujuk"]) or "tidak ada rujukan KB")
    if res["eskalasi"]:
        msg += "\nStatus: DIESKALASI ke staf (simulasi)"
    if res["sumber"] != "llm":
        msg += f"\n[mode: {res['sumber']}]"
    await update.message.reply_text(msg + SIM)
    if res["eskalasi"] and ADMIN and ADMIN != update.effective_chat.id:
        await ctx.bot.send_message(ADMIN, f"[ESKALASI]\nPertanyaan: {q[:300]}\nKB: {', '.join(res['kb_dirujuk']) or '-'}")


async def prospek(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    raw = " ".join(ctx.args) if ctx.args else ""
    parts = [("" if p.strip() == "-" else p.strip()) for p in raw.split("|")] + [""] * 4
    nama, email, phone, minat = parts[:4]
    try:
        pid, created = core.upsert_prospek(nama, email, phone, minat, chat)
    except ValueError as e:
        await update.message.reply_text(f"Gagal: {e}\nFormat: /prospek Nama | email | telepon | minat")
        return
    await update.message.reply_text(
        f"Prospek #{pid} {'BARU dicatat' if created else 'sudah ada, data DIPERBARUI (tidak digandakan)'}. "
        f"Total prospek unik di chat ini: {core.count_prospek(chat)}.")
    d = await asyncio.to_thread(core.make_draft, pid)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Setujui (simulasi)", callback_data=f"ok:{d['id']}"),
                                InlineKeyboardButton("Tolak", callback_data=f"no:{d['id']}")]])
    await ctx.bot.send_message(
        ADMIN or chat, f"DRAF #{d['id']} untuk prospek #{pid}  |  status: MENUNGGU PERSETUJUAN\n"
                       f"Sumber draf: {d['sumber']}  |  KB: {', '.join(d['kb_dirujuk'])}\n\n{d['isi']}{SIM}",
        reply_markup=kb)


async def on_decision(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if ADMIN and q.from_user.id != ADMIN:
        await q.answer("Hanya staf yang boleh memutuskan.", show_alert=True)
        return
    action, did = q.data.split(":")
    try:
        st = core.decide_draft(int(did), action == "ok", None if ADMIN else q.message.chat.id)
    except ValueError as e:
        await q.answer(str(e), show_alert=True)
        return
    await q.answer()
    note = ("DISETUJUI (simulasi): TIDAK ada pesan yang dikirim ke prospek."
            if st == "disetujui_simulasi" else "DITOLAK.")
    await q.edit_message_text(q.message.text.replace("MENUNGGU PERSETUJUAN", st.upper()) + f"\n\n{note}")


async def jumlah(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Prospek unik di chat ini: {core.count_prospek(update.effective_chat.id)}")


async def draf(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    with core.db() as c:
        rows = c.execute("SELECT id, prospek_id FROM draf WHERE status='menunggu_persetujuan' AND chat_id=?",
                         (str(update.effective_chat.id),)).fetchall()
    await update.message.reply_text(
        "Draf menunggu persetujuan: " + (", ".join(f"#{r['id']} (prospek #{r['prospek_id']})" for r in rows) or "tidak ada"))


def main():
    app = ApplicationBuilder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("prospek", prospek))
    app.add_handler(CommandHandler("jumlah", jumlah))
    app.add_handler(CommandHandler("draf", draf))
    app.add_handler(CallbackQueryHandler(on_decision, pattern=r"^(ok|no):\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    base = os.getenv("WEBHOOK_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if base:  # hosting: Telegram yang memanggil server, jadi server tidur bisa dibangunkan oleh pesan masuk
        secret = re.sub(r"[^A-Za-z0-9_-]", "", os.environ["WEBHOOK_SECRET"])
        path = "hook-" + secret[:20]
        app.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", "10000")), url_path=path,
                        webhook_url=f"{base.rstrip('/')}/{path}", secret_token=secret)
    else:  # lokal
        app.run_polling()


if __name__ == "__main__":
    main()
