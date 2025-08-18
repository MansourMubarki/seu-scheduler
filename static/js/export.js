// export.js v24 — تصدير بدون قص للجوال واللاب (Plan A: html-to-image, Plan B: html2canvas)
// يعالج: مساحة العمل، انتظار الخطوط، overflow، عرض 7 أعمدة كامل.
(function () {
  const BG = "#FFFFFF";
  const SCALE = Math.max(2, Math.min(3, window.devicePixelRatio || 2));
  const MIN_TABLE_WIDTH = 1260; // 7 أيام × 180px

  function getSource() {
    const src = document.getElementById("capture");
    if (!src) throw new Error("لم يتم العثور على #capture");
    return src;
  }

  function ensureWorkspace() {
    let ws = document.getElementById("export-work");
    if (!ws) {
      ws = document.createElement("div");
      ws.id = "export-work";
      document.body.appendChild(ws);
    }
    // مهم: نخليه مرئي لكن خارج الشاشة (علشان التخطيط يتم)، بدون z-index سالب
    ws.style.position = "fixed";
    ws.style.left = "-99999px";
    ws.style.top = "0";
    ws.style.visibility = "visible";
    ws.style.pointerEvents = "none";
    ws.style.background = BG;
    ws.innerHTML = "";
    return ws;
  }

  function relaxOverflows(root) {
    root.querySelectorAll("*").forEach(el => {
      const cs = window.getComputedStyle(el);
      if (/(hidden|auto|scroll)/.test(cs.overflow) || /(hidden|auto|scroll)/.test(cs.overflowX) || /(hidden|auto|scroll)/.test(cs.overflowY)) {
        el.style.overflow = "visible";
        el.style.overflowX = "visible";
        el.style.overflowY = "visible";
        el.style.maxWidth = "none";
      }
      if (cs.transform !== "none") el.style.transform = "none";
      if (cs.position === "fixed") el.style.position = "static";
    });
  }

  function calcFullWidth(source) {
    const table = source.querySelector(".schedule-table") || source;
    // نضمن على الأقل عرض 7 أعمدة
    return Math.max(MIN_TABLE_WIDTH, table.scrollWidth, source.scrollWidth, table.getBoundingClientRect().width);
  }

  function makeClone(source) {
    const ws = ensureWorkspace();
    const width = calcFullWidth(source);

    const wrap = document.createElement("div");
    wrap.className = "export-clone";
    wrap.style.background = BG;
    wrap.style.display = "block";
    wrap.style.boxSizing = "border-box";
    wrap.style.padding = "12px";
    wrap.style.width = width + "px";
    wrap.dir = "rtl";

    const clone = source.cloneNode(true);
    clone.id = "capture-export";
    clone.classList.add("export-mode");
    clone.style.width = width + "px";
    clone.style.minWidth = width + "px";
    clone.style.maxWidth = "none";
    clone.style.position = "static";
    clone.style.transform = "none";
    clone.setAttribute("dir", "rtl");

    const table = clone.querySelector(".schedule-table");
    if (table) {
      table.style.width = width + "px";
      table.style.minWidth = width + "px";
      table.style.maxWidth = "none";
      table.style.tableLayout = "auto";
      const colW = Math.floor(width / 7);
      table.querySelectorAll("th,td").forEach(cell => cell.style.width = colW + "px");
    }

    // عوّم الشعار ليكون من نفس الأصل (لو عندك شعار خارجي استبدله بصورة محلية)
    clone.querySelectorAll("img").forEach(img => {
      if (img.src.startsWith("http") && !img.src.startsWith(location.origin)) {
        img.crossOrigin = "anonymous";
      }
    });

    relaxOverflows(clone);
    wrap.appendChild(clone);
    ws.appendChild(wrap);

    // بعد الإلحاق، نقرأ الارتفاع الحقيقي
    const height = Math.max(clone.scrollHeight, clone.clientHeight, clone.getBoundingClientRect().height);
    return { node: clone, width, height };
  }

  async function waitFonts() {
    if (document.fonts && document.fonts.ready) {
      try { await document.fonts.ready; } catch {}
    } else {
      await new Promise(r => setTimeout(r, 150));
    }
  }

  async function loadHtmlToImage() {
    if (window.htmlToImage) return;
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://unpkg.com/html-to-image@1.11.11/dist/html-to-image.min.js";
      s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function toCanvas_htmlToImage(prep) {
    await loadHtmlToImage();
    await waitFonts();

    const { node, width, height } = prep;
    const dataUrl = await window.htmlToImage.toPng(node, {
      backgroundColor: BG,
      width, height,
      canvasWidth: Math.round(width * SCALE),
      canvasHeight: Math.round(height * SCALE),
      pixelRatio: SCALE,
      skipAutoScale: true,
      cacheBust: true,
      style: { transform: "none" }
    });

    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = dataUrl; });
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    return canvas;
  }

  async function toCanvas_html2canvas(prep) {
    if (!window.html2canvas) throw new Error("html2canvas غير محمّل");
    await waitFonts();
    const { node, width } = prep;
    const height = Math.max(node.scrollHeight, node.clientHeight);
    return await html2canvas(node, {
      scale: SCALE,
      backgroundColor: BG,
      useCORS: true,
      allowTaint: true,
      foreignObjectRendering: false,
      width, height,
      windowWidth: width, windowHeight: height,
      scrollX: 0, scrollY: 0
    });
  }

  async function toCanvas(prep) {
    // Plan A
    try {
      const c = await toCanvas_htmlToImage(prep);
      if (c && c.width > 10 && c.height > 10) return c;
      throw new Error("empty canvas (html-to-image)");
    } catch (e1) {
      console.warn("[Export] html-to-image failed → trying html2canvas", e1);
      // Plan B
      const c2 = await toCanvas_html2canvas(prep);
      if (!c2 || c2.width <= 10 || c2.height <= 10) throw new Error("empty canvas (html2canvas)");
      return c2;
    }
  }

  function cleanup(){ const ws=document.getElementById("export-work"); if(ws) ws.innerHTML=""; }

  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.download = filename; a.href = url;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }

  function bind(id, handler){
    const btn=document.getElementById(id);
    if(!btn) return;
    btn.addEventListener("click", async (e)=>{
      e.preventDefault();
      try{
        const prep = makeClone(getSource());
        const canvas = await toCanvas(prep);
        await handler(canvas);
      } catch(err){
        console.error("[Export] Error:", err);
        alert("تعذّر حفظ الجدول. فضلاً حدّث الصفحة وجرب مرة أخرى.");
      } finally { cleanup(); }
    });
  }

  window.addEventListener("DOMContentLoaded", ()=>{
    bind("btnPNG", async (canvas)=>{
      if (canvas.toBlob) canvas.toBlob(b=>downloadBlob("SEU-schedule.png", b), "image/png", 1.0);
      else {
        const a=document.createElement("a");
        a.download="SEU-schedule.png"; a.href=canvas.toDataURL("image/png",1.0);
        document.body.appendChild(a); a.click(); a.remove();
      }
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