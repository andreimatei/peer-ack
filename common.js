function toggle_menu_buttons() {
  let ack_link = document.getElementById('ack_menu_btn')
  let my_acks_link = document.getElementById('my_acks_menu_btn')
  let report_link = document.getElementById('report_menu_btn')
  let ack_enabled = (cur_page != "ack")
  let my_acks_enabled = (cur_page != "my_acks")
  let report_enabled = (cur_page != "report")
  if (ack_enabled) {
      ack_link.style["pointer-events"] = "";
      ack_link.style["text-decoration"] = "";
  } else {
      ack_link.style["pointer-events"] = "none";
      ack_link.style["text-decoration"] = "none";
  }
  if (my_acks_enabled) {
      my_acks_link.style["pointer-events"] = "";
      my_acks_link.style["text-decoration"] = "";
  } else {
      my_acks_link.style["pointer-events"] = "none";
      my_acks_link.style["text-decoration"] = "none";
  }
  if (my_acks_enabled) {
      my_acks_link.style["pointer-events"] = "";
      my_acks_link.style["text-decoration"] = "";
  } else {
      my_acks_link.style["pointer-events"] = "none";
      my_acks_link.style["text-decoration"] = "none";
  }
  if (report_link) {
    if (report_enabled) {
        report_link.style["pointer-events"] = "";
        report_link.style["text-decoration"] = "";
    } else {
        report_link.style["pointer-events"] = "none";
        report_link.style["text-decoration"] = "none";
    }
  }
}

window.addEventListener("load",
  function() {
      toggle_menu_buttons();
  });
            
function ack_click() {
  window.location.href = "/ack"
}
