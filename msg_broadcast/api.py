import frappe
from frappe.utils import now


# =====================================================
# ACK BROADCAST (บันทึกว่าผู้ใช้กดรับทราบแล้ว)
# =====================================================

@frappe.whitelist()
def ack_broadcast(broadcast):

    user = frappe.session.user

    # กันซ้ำ (user เดิม + broadcast เดิม)
    if frappe.db.exists("MSG Broadcast Log", {
        "user": user,
        "broadcast": broadcast
    }):
        return "already"

    frappe.get_doc({
        "doctype": "MSG Broadcast Log",
        "user": user,
        "broadcast": broadcast,
        "acknowledged_on": now(),
        "ip_address": frappe.local.request_ip
    }).insert(ignore_permissions=True)

    return "ok"


# =====================================================
# RENDER HTML MESSAGE
# =====================================================

def render_html(message):

    message = message or ""
    message = message.replace("'", "’")

    return f"""
    <div style="border-left:4px solid #0b5ed7;
        background:#f0f7ff;
        padding:14px;
        border-radius:8px;
        font-size:14px;
        line-height:1.6;">

        <div style="font-weight:bold;color:#0b5ed7;margin-bottom:6px;">
            📢 ประกาศจากฝ่าย IT
        </div>

        <div>
            {message}
        </div>

        <div style="margin-top:10px;font-size:12px;color:#666;">
            IT Team • {now()}
        </div>
    </div>
    """


# =====================================================
# SEND FORCE DIALOG (1 ครั้งต่อ user)
# =====================================================

@frappe.whitelist()
def send_force_dialog(docname):

    doc = frappe.get_doc("Message Broadcast", docname)
    html = render_html(doc.message)

    users = frappe.get_all(
        "User",
        filters={"enabled": 1},
        pluck="name"
    )

    # ❗ ใช้ format แทน f-string เพื่อไม่ชน { } ของ JS
    js = """
    (function () {{

        const broadcast = "{docname}";
        const tabKey = "broadcast_tab_" + broadcast;
        const doneKey = "broadcast_done_" + broadcast;

        // ถ้า tab นี้เคยเปิดแล้ว
        if (sessionStorage.getItem(tabKey)) {{
            return;
        }}

        // เช็คว่า user เคยกดรับทราบแล้วหรือยัง
        frappe.call({{
            method: "frappe.client.get_count",
            args: {{
                doctype: "MSG Broadcast Log",
                filters: {{
                    user: frappe.session.user,
                    broadcast: broadcast
                }}
            }},
            callback(r) {{
                if (r.message > 0) {{
                    return;
                }}
                showDialog();
            }}
        }});

        function showDialog() {{

            sessionStorage.setItem(tabKey, "1");

            let counter = 5;

            let d = new frappe.ui.Dialog({{
                title: "ประกาศสำคัญ",
                static: true,
                no_cancel: true,
                fields: [
                    {{
                        fieldtype: "HTML",
                        fieldname: "content",
                        options: `{html}`
                    }}
                ],
                primary_action_label: "รับทราบ (5)",
                primary_action() {{
                    frappe.call({{
                        method: "msg_broadcast.api.ack_broadcast",
                        args: {{
                            broadcast: broadcast
                        }}
                    }});
                    localStorage.setItem(doneKey, Date.now());
                    d.hide();
                }}
            }});

            d.show();

            // นับถอยหลัง 5 วินาที
            let btn = d.get_primary_btn();
            btn.prop("disabled", true);

            let timer = setInterval(function () {{
                counter -= 1;
                btn.text("รับทราบ (" + counter + ")");

                if (counter <= 0) {{
                    clearInterval(timer);
                    btn.text("รับทราบ");
                    btn.prop("disabled", false);
                }}
            }}, 1000);

            // ถ้า tab อื่นกดรับทราบ → ปิดอัตโนมัติ
            window.addEventListener("storage", function (e) {{
                if (e.key === doneKey) {{
                    d.hide();
                }}
            }});

            // ปุ่มติดต่อ IT
            d.add_custom_action("ติดต่อ IT", function () {{
                frappe.msgprint({{
                    title: "IT Support",
                    message:
                        "📞 โทร: 02-xxx-xxxx<br>" +
                        "📧 Email: it@company.com"
                }});
            }});
        }}

    }})();
    """.format(
        docname=docname,
        html=html
    )

    for u in users:
        frappe.publish_realtime("eval_js", js, user=u)

    doc.status = "Sent"
    doc.sent_on = now()
    doc.save(ignore_permissions=True)

    return {"status": "success"}
