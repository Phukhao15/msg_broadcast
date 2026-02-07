frappe.ui.form.on('Message Broadcast', {
	refresh(frm) {

		if (frm.doc.status !== "Sent") {
			frm.add_custom_button("Send Broadcast", () => {
				frappe.call({
					method: "msg_broadcast.api.send_force_dialog",
					args: {
						docname: frm.doc.name
					},
					callback() {
						frappe.msgprint("ส่งข้อความเรียบร้อย");
						frm.reload_doc();
					}
				});
			}).addClass("btn-primary");
		}

		frm.add_custom_button("View Ack Log", () => {
			frappe.set_route("List", "MSG Broadcast Log", {
				broadcast: frm.doc.name
			});
		});
	}
});
