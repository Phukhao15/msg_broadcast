import frappe
from frappe.utils import now


# =====================================
# SAVE ACK (กันซ้ำ / multi-tab safe)
# =====================================

@frappe.whitelist()
def ack_broadcast(broadcast):

    user = frappe.session.user

    if not user or user == "Guest":
        return "guest"

    # กัน insert ซ้ำ (DB level)
    exists = frappe.db.exists(
        "MSG Broadcast Log",
        {
            "user": user,
            "broadcast": broadcast
        }
    )

    if exists:
        return "already"

    frappe.get_doc({
        "doctype": "MSG Broadcast Log",
        "user": user,
        "broadcast": broadcast,
        "acknowledged_on": now(),
        "ip_address": frappe.local.request_ip
    }).insert(ignore_permissions=True)

    return "ok"


# =====================================
# RENDER HTML (safe)
# =====================================

def render_template(msg):

    msg = frappe.utils.escape_html(msg or "")

    return f"""
    <div style="
        border-left:4px solid #0b5ed7;
        background:#f0f7ff;
        padding:14px;
        border-radius:8px;
        font-size:14px;
        line-height:1.6;
    ">
        <div style="font-weight:bold;color:#0b5ed7;">
            📢 ประกาศจากฝ่าย ERPNEXT
        </div>

        <div style="margin-top:8px;">
            {msg}
        </div>

        <div style="margin-top:10px;font-size:12px;color:#666;">
            IT Team • {now()}
        </div>
    </div>
    """


# =====================================
# SEND FORCE DIALOG
# =====================================

@frappe.whitelist()
def send_force_dialog(docname):

    doc = frappe.get_doc("Message Broadcast", docname)

    if doc.status == "Sent":
        return {"status": "already_sent"}

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["!=", "Guest"]},
        pluck="name"
    )

    html = render_template(doc.message)

    # NOTE: JS จะรันฝั่ง client
    js = f"""
(function(){{
    let broadcast = "{docname}";
    let tabKey = "broadcast_tab_" + broadcast;
    let doneKey = "broadcast_done_" + broadcast;

    // ถ้าเคย ACK แล้ว ไม่ต้องแสดง
    if (localStorage.getItem(doneKey)) {{
        return;
    }}

    // ป้องกันแสดงซ้ำใน tab เดียว
    if (sessionStorage.getItem(tabKey)) {{
        return;
    }}

    sessionStorage.setItem(tabKey, "1");

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
                localStorage.setItem(doneKey, "1");
                return;
            }}
            showDialog();
        }}
    }});

    function showDialog() {{

        let counter = 5;

        let d = new frappe.ui.Dialog({{
            title: "ประกาศสำคัญ",
            static: true,
            no_cancel: true,
            fields: [{{
                fieldtype: "HTML",
                fieldname: "content",
                options: `{html}`
            }}],
            primary_action_label: "รับทราบ (5)",
            primary_action() {{
                frappe.call({{
                    method: "itg.api.ack_broadcast",
                    args: {{ broadcast: broadcast }}
                }});

                localStorage.setItem(doneKey, Date.now());
                d.hide();
            }}
        }});

        d.show();

        let btn = d.get_primary_btn();
        btn.prop("disabled", true);

        let t = setInterval(function(){{
            counter--;
            btn.text("รับทราบ (" + counter + ")");
            if (counter <= 0) {{
                clearInterval(t);
                btn.text("รับทราบ");
                btn.prop("disabled", false);
            }}
        }}, 1000);

        // ถ้า ACK จาก tab อื่น → ปิด dialog นี้
        window.addEventListener("storage", function(e) {{
            if (e.key === doneKey) {{
                d.hide();
            }}
        }});

        // ปุ่มติดต่อ IT
        d.add_custom_action("ติดต่อ IT", function(){{
            frappe.msgprint({{
                title: "IT Support",
                message:
                    "📞 โทร: 02-xxx-xxxx<br>" +
                    "📧 Mail: it@company.com"
            }});
        }});
    }}
})();
"""

    for u in users:
        frappe.publish_realtime("eval_js", js, user=u)

    doc.status = "Sent"
    doc.sent_on = now()
    doc.save(ignore_permissions=True)

    return {"status": "success", "users": len(users)}
