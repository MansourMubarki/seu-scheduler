// export.js v25 — تصدير بدون قص للجوال واللاب (Workspace + scale + overflow fixes)
(function () {
  const SCALE = Math.max(2, Math.min(3, window.devicePixelRatio || 2));
  function getCapture() {
    const el = document.getElementById("capture");
    if (!el) throw new Error("لم يتم العثور على #capture");
    return el;
  }
  function ensureWorkspace() {
    let ws = document.getElementById("export-work");
    if (!ws) {
      ws = document.createElement("div");
      ws.id = "export-work";
      document.body.appendChild(ws);
    }
    return ws;
  }
  function wait(ms){ return new Promise(r=>setTimeout(r,ms)); }
  async function toCanvas(srcEl) {
    const clone = srcEl.cloneNode(true);
    clone.classList.add("export-clone");
    clone.style.width = srcEl.scrollWidth + "px";
    const ws = ensureWorkspace();
    ws.appendChild(clone);
    document.documentElement.classList.add("export-mode");
    await wait(50);
    try {
      const canvas = await html2canvas(clone, {
        backgroundColor: "#FFFFFF",
        scale: SCALE,
        useCORS: true,
        allowTaint: true,
        scrollX: 0, scrollY: 0,
        windowWidth: Math.max(document.documentElement.scrollWidth, clone.scrollWidth),
        windowHeight: Math.max(document.documentElement.scrollHeight, clone.scrollHeight)
      });
      return canvas;
    } finally {
      document.documentElement.classList.remove("export-mode");
      clone.remove();
    }
  }
  function downloadBlob(name, blob) {
    const a = document.createElement("a"); a.download = name;
    a.href = URL.createObjectURL(blob); document.body.appendChild(a); a.click();
    setTimeout(()=>URL.revokeObjectURL(a.href), 1000); a.remove();
  }
  function bind(id, handler) {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", async ()=>{
      try {
        const canvas = await toCanvas(getCapture());
        await handler(canvas);
      } catch (e) {
        console.error(e);
        alert("تعذّر حفظ الجدول. جرّب تحديث الصفحة.");
      }
    });
  }
  window.addEventListener("DOMContentLoaded", ()=>{
    bind("btnPNG", async (canvas)=>{
      if (canvas.toBlob) canvas.toBlob(b=>downloadBlob("SEU-schedule.png", b), "image/png", 1.0);
      else downloadBlob("SEU-schedule.png", dataURLToBlob(canvas.toDataURL("image/png",1.0)));
    });
    bind("btnPDF", async (canvas)=>{
      if (!window.jspdf || !window.jspdf.jsPDF) throw new Error("jsPDF غير محمّل");
      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF({ orientation:"landscape", unit:"pt", format:"a4" });
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const margin = 24;
      const maxW = pageW - margin*2;
      const maxH = pageH - margin*2;
      const ratio = canvas.height / canvas.width;
      let drawW = maxW, drawH = drawW * ratio;
      if (drawH > maxH) { drawH = maxH; drawW = drawH / ratio; }
      const x = (pageW - drawW)/2, y = (pageH - drawH)/2;
      pdf.addImage(canvas.toDataURL("image/png",1.0), "PNG", x, y, drawW, drawH, undefined, "FAST");
      pdf.save("SEU-schedule.pdf");
    });
  });
})();