"""Uji A1 offline (LLM dipalsukan agar hasil bisa diulang). Jalankan: python test_a1.py"""
import json
import os
import tempfile

os.environ["A1_DB"] = os.path.join(tempfile.mkdtemp(), "uji.db")
import core  # noqa: E402

rows = []


def check(nama, cond, detail=""):
    rows.append((nama, "LULUS" if cond else "GAGAL", detail))


def fake(jawaban, refs, esc=False):
    return lambda _p: json.dumps({"jawaban": jawaban, "kb_dirujuk": refs, "eskalasi": esc})


def boom(_p):
    raise RuntimeError("API mati")


# 1-4: pertanyaan wajib
r = core.answer("Apakah saya harus sponsor?", fake("Tidak wajib; sponsorship opsional dan tidak menentukan hasil.", ["KB03"]))
check("U1 harus sponsor?", r["kb_dirujuk"] == ["KB03"] and not r["eskalasi"], f'{r["kb_dirujuk"]} esc={r["eskalasi"]}')
r = core.answer("Apakah dijamin bintang 5?", fake("Kepastian penghargaan belum tersedia, diteruskan ke staf.", ["KB04"], True))
check("U2 dijamin bintang 5?", r["kb_dirujuk"] == ["KB04"] and r["eskalasi"], f'{r["kb_dirujuk"]} esc={r["eskalasi"]}')
r = core.answer("Berapa harga dan tanggal wawancara?", fake("Detail diteruskan ke staf.", ["KB04"], False))
check("U3 harga + tanggal (LLM lupa eskalasi)", set(r["kb_dirujuk"]) == {"KB04", "KB02"} and r["eskalasi"],
      f'{r["kb_dirujuk"]} esc={r["eskalasi"]} (pagar aturan menutup kesalahan LLM)')
r = core.answer("Apakah pendaftaran berbayar?", fake("Pendaftaran tes tidak berbiaya.", ["KB01"]))
check("U4 pendaftaran berbayar?", r["kb_dirujuk"] == ["KB01"] and not r["eskalasi"], f'{r["kb_dirujuk"]}')

# 5-9: kegagalan dan guard
r = core.answer("Berapa harga paketnya?", boom)
check("G1 API mati, pertanyaan harga", r["sumber"] == "fallback" and r["eskalasi"] and "KB04" in r["kb_dirujuk"], r["jawaban"][:60])
r = core.answer("Apakah ada diskon akhir tahun?", boom)
check("G2 API mati, di luar KB", r["eskalasi"] and not r["kb_dirujuk"], r["jawaban"][:60])
r = core.answer("Bagaimana peluang saya?", fake("Dijamin bintang 5, paket Rp5 juta.", ["KB04"]))
check("G3 LLM mengarang harga/jaminan", r["sumber"] == "guard" and "Rp" not in r["jawaban"] and r["eskalasi"], r["catatan"])
r = core.answer("Apa itu awards?", fake("Awards itu bagus.", []))
check("G4 jawaban tanpa rujukan KB", r["sumber"] == "guard" and r["eskalasi"], r["catatan"])
r = core.answer("Apakah gratis?", fake("Gratis.", ["KB99"]))
check("G5 LLM merujuk KB palsu", r["sumber"] == "fallback" and r["kb_dirujuk"] == ["KB01"], r["catatan"])
r = core.answer("Apakah gratis?", lambda _p: "bukan json {{")
check("G6 JSON rusak", r["sumber"] == "fallback", r["catatan"][:40])

# 10-12: duplikasi prospek
a = core.upsert_prospek("Surya Reka", "Info@SuryaReka.test", "0812-3456-7890", "ESG")
b = core.upsert_prospek("Surya Reka", " info@suryareka.test ", "", "ESG")
c = core.upsert_prospek("Surya Reka PT", "", "+62 812 3456 7890", "")
check("D1 email beda huruf/spasi = sama", a[0] == b[0] and a[1] and not b[1])
check("D2 telepon format beda = sama", a[0] == c[0] and not c[1])
core.upsert_prospek("Tani Makmur", "a@tani.test")
core.upsert_prospek("Tani Makmur", "a@tani.test")
core.upsert_prospek("Tani Makmur", "a@tani.test")
check("D3 masuk 3x tetap 1 baris", core.count_prospek() == 2, f"total unik={core.count_prospek()}")
try:
    core.upsert_prospek("X", "bukan-email", "")
    ok = False
except ValueError:
    ok = True
check("D4 email tidak valid ditolak", ok)

# 13-15: draf menunggu persetujuan
d = core.make_draft(a[0], fake("Halo Surya Reka, pendaftaran tes tidak berbiaya (KB01).", ["KB01"]))
with core.db() as conn:
    st = conn.execute("SELECT status FROM draf WHERE id=?", (d["id"],)).fetchone()[0]
check("P1 draf baru = menunggu persetujuan", st == "menunggu_persetujuan")
d2 = core.make_draft(a[0], boom)
check("P2 LLM gagal, draf template", d2["sumber"] == "template")
check("P3 setujui = tanda simulasi", core.decide_draft(d["id"], True) == "disetujui_simulasi")
try:
    core.decide_draft(d["id"], False)
    ok = False
except ValueError:
    ok = True
check("P4 keputusan tidak bisa diubah/diulang", ok)

# 16-19: isolasi chat, kepemilikan draf, kuota demo
x1 = core.upsert_prospek("Laut Biru", "x@laut.test", "", "", chat_id="evaluator1")
x2 = core.upsert_prospek("Laut Biru", "x@laut.test", "", "", chat_id="evaluator2")
check("I1 chat berbeda = data terpisah", x1[0] != x2[0] and x1[1] and x2[1]
      and core.count_prospek("evaluator1") == 1 and core.count_prospek("evaluator2") == 1)
dd = core.make_draft(x1[0], boom)
try:
    core.decide_draft(dd["id"], True, chat_id="evaluator2")
    ok = False
except ValueError:
    ok = True
check("I2 chat lain tidak bisa menyetujui draf", ok)
check("I3 pemilik draf bisa menyetujui", core.decide_draft(dd["id"], True, chat_id="evaluator1") == "disetujui_simulasi")
core.PER_CHAT_HOUR = 0
r = core.answer("Apakah gratis?", None, "evaluator9")
check("K1 kuota habis, mode aturan KB tetap jawab", r["sumber"] == "fallback" and r["kb_dirujuk"] == ["KB01"]
      and "kuota" in r["catatan"], r["catatan"][:50])

print(f'{"UJI":42} {"HASIL":6} DETAIL')
for n, s, dt in rows:
    print(f"{n:42} {s:6} {dt}")
print(f'\n{sum(r[1]=="LULUS" for r in rows)}/{len(rows)} lulus')
